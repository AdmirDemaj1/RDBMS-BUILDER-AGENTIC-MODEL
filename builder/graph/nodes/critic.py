# graph/nodes/critic.py
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import GraphState, CriticReport, Severity
from ...utils.llm import get_llm
from ...utils.state_manager import StateManager
from ...utils.context_builder import ContextBuilder
from ...utils.task_manager import start_task, complete_task, fail_task
from pydantic import BaseModel, Field


class FeedbackItem(BaseModel):
    target: str
    severity: Severity
    issue: str
    recommendation: str


class CriticEvaluation(BaseModel):
    overall_score: int = Field(ge=1, le=10, description="1-10 score, give credit for improvements")
    feedback_items: List[FeedbackItem]
    summary: str
    requires_revision: bool
    improvements_from_previous: List[str] = Field(default=[], description="What got better since last evaluation")


CRITIC_PROMPT = """You are a senior database architect evaluating database schemas. Your goal is to provide 
constructive feedback that guides improvement while acknowledging what's already done well.

## SCORING GUIDELINES (CRITICAL - Read Carefully):
- **1-3**: Fundamentally broken, missing core requirements (no PKs, no FKs, no indexes)
- **4-5**: Has critical production blockers (missing FK indexes, no audit trail, security issues)
- **6-7**: Production-ready but has optimization opportunities
- **8-9**: Well-designed with only minor suggestions
- **10**: Exemplary design following all best practices

## EVALUATION CRITERIA

### 1. Data Integrity (Critical):
- Primary keys on all tables
- Foreign key constraints properly defined
- Unique constraints on natural keys (email, license_plate, etc.)
- Appropriate nullability settings

### 2. Performance (Critical):
- Indexes on **ALL** foreign key columns (missing FK index = automatic CRITICAL)
- Composite indexes for common query patterns
- Appropriate data types for scale

### 3. Audit & Compliance (Important):
- created_at and updated_at on all tables
- Soft delete capability (deleted_at) where needed
- PII identified and marked

### 4. Security (Important):
- PII protection strategy (RLS, encryption markers)
- Multi-tenant isolation (RLS on tenant tables)

### 5. Best Practices (Nice to have):
- Timezone-aware timestamps (TIMESTAMPTZ)
- Decimal for financial data
- Check constraints on enums

## IMPORTANT - When Evaluating a Refined Schema:
- **Compare it to the previous version** if this is iteration 2+
- **Give credit for improvements made** - if indexes were added, acknowledge it
- **Adjust score UPWARD** if critical issues were fixed (e.g., 4→7 if all FK indexes added)
- **Focus new feedback on remaining issues only** - don't repeat already-fixed issues
- **If all critical issues are resolved, score should be 6+**
- **List improvements_from_previous** to show what got better

## Revision Logic:
- Set requires_revision=true ONLY if: score < 7 OR critical issues remain
- If score ≥ 7 and only warnings/suggestions remain: requires_revision=false

Format your response with specific, actionable feedback."""


def critic(state: GraphState) -> GraphState:
    start_task(state, "critic")
    
    if not state["working"].get("tables"):
        complete_task(state, "critic", "No schema to evaluate")
        return state
    
    print("\n🔍 CRITIC EVALUATION")
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(CriticEvaluation)
    
    context = ContextBuilder.for_critic(state)
    
    messages = [
        SystemMessage(content=CRITIC_PROMPT),
        HumanMessage(content=context)
    ]
    
    try:
        result = structured_llm.invoke(messages)
        StateManager.increment_llm_calls(state)
        
        report: CriticReport = {
            "overall_score": result.overall_score,
            "feedback_items": [
                {
                    "target": f.target,
                    "severity": f.severity.value,
                    "issue": f.issue,
                    "recommendation": f.recommendation,
                    "applied": False
                }
                for f in result.feedback_items
            ],
            "summary": result.summary,
            "requires_revision": result.requires_revision
        }
        
        StateManager.add_critic_report(state, report)
        
        critical = len([f for f in report["feedback_items"] if f["severity"] == "critical"])
        warnings = len([f for f in report["feedback_items"] if f["severity"] == "warning"])
        
        # Check if this is a refinement iteration
        critic_reports = state["archive"].get("critic_reports", [])
        is_refinement = len(critic_reports) > 1
        
        print(f"   Score: {result.overall_score}/10")
        print(f"   Issues: {critical} critical, {warnings} warnings")
        
        # Show improvements if this is a refinement iteration
        if is_refinement and result.improvements_from_previous:
            print(f"   ✨ Improvements recognized:")
            for imp in result.improvements_from_previous[:3]:  # Show first 3
                print(f"      - {imp}")
            if len(result.improvements_from_previous) > 3:
                print(f"      ... and {len(result.improvements_from_previous) - 3} more")
        
        print(f"   Revision: {'Required' if result.requires_revision else 'Not needed'}")
        
        state["working"]["current_step"] = "critic_complete"
        complete_task(state, "critic", f"Score {result.overall_score}/10")
        
    except Exception as e:
        fail_task(state, "critic", str(e))
        state["working"]["current_step"] = "critic_failed"
    
    return state