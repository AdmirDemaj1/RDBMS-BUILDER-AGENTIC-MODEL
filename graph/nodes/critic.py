# graph/nodes/critic.py
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import GraphState, CriticReport, Severity
from utils.llm import get_llm
from utils.state_manager import StateManager
from utils.context_builder import ContextBuilder
from utils.task_manager import start_task, complete_task, fail_task
from pydantic import BaseModel, Field


class FeedbackItem(BaseModel):
    target: str
    severity: Severity
    issue: str
    recommendation: str


class CriticEvaluation(BaseModel):
    overall_score: int = Field(ge=1, le=10)
    feedback_items: List[FeedbackItem]
    summary: str
    requires_revision: bool


CRITIC_PROMPT = """Evaluate schema for PRODUCTION READINESS (1-10).

## PERFORMANCE EVALUATION (30%)
Critical checks:
- Every FK column MUST have an index (missing = critical)
- Columns in WHERE/ORDER BY should have indexes
- Composite indexes for common query patterns
- No missing indexes on high-cardinality columns (user_id, order_id)
- TIMESTAMPTZ used instead of TIMESTAMP
- UUID vs BIGSERIAL choice appropriate for scale

Warning signs:
- Tables without any indexes (except PK)
- Over-indexing (>5 indexes per table without justification)
- Missing partial indexes for status-filtered queries

## SECURITY EVALUATION (25%)
Critical checks:
- PII columns identified (email, phone, address, ssn, ip_address)
- Multi-tenant tables should enable Row Level Security
- Sensitive data columns flagged for encryption consideration

Warning signs:
- Missing CHECK constraints on status/enum columns
- No ON DELETE action specified for FKs
- Cascading deletes on sensitive data without audit

## DATA INTEGRITY (25%)
Critical checks:
- All tables have id (UUID/BIGSERIAL), created_at, updated_at
- FKs properly reference existing tables
- NOT NULL on required business fields
- UNIQUE on natural keys (email, username, sku)

Warning signs:
- Missing soft delete (deleted_at) on important entities
- No version column for optimistic locking on concurrent-update tables
- Nullable FKs that should be required

## DESIGN QUALITY (20%)
Check:
- 3NF normalization (no redundancy)
- Naming: plural tables, singular columns, snake_case
- Appropriate data types (DECIMAL for money, not FLOAT)
- Junction tables for M:N with proper structure

## SCORING
- 9-10: Production-ready, optimized, secure
- 7-8: Good, minor optimizations needed
- 5-6: Functional but performance/security gaps
- <5: Major issues, not production-safe

Set requires_revision=true if: score<7, any critical issues, or missing indexes on FKs."""


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
        
        print(f"   Score: {result.overall_score}/10")
        print(f"   Issues: {critical} critical, {warnings} warnings")
        print(f"   Revision: {'Required' if result.requires_revision else 'Not needed'}")
        
        state["working"]["current_step"] = "critic_complete"
        complete_task(state, "critic", f"Score {result.overall_score}/10")
        
    except Exception as e:
        fail_task(state, "critic", str(e))
        state["working"]["current_step"] = "critic_failed"
    
    return state