# graph/nodes/critic.py
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import GraphState, CriticFeedback, CriticReport
from utils.llm import get_llm
from utils.task_manager import start_task, complete_task, fail_task
from pydantic import BaseModel, Field
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"


class FeedbackItem(BaseModel):
    target: str = Field(description="What is being critiqued: 'entities', 'relationships', 'schema', 'naming', 'normalization', 'performance'")
    severity: Severity = Field(description="Severity level of the issue")
    issue: str = Field(description="Clear description of the problem")
    recommendation: str = Field(description="Specific actionable fix")


class CriticEvaluation(BaseModel):
    overall_score: int = Field(description="Quality score from 1-10", ge=1, le=10)
    feedback_items: List[FeedbackItem] = Field(description="List of feedback items")
    summary: str = Field(description="Brief overall assessment")
    requires_revision: bool = Field(description="Whether schema needs revision before proceeding")


CRITIC_SYSTEM_PROMPT = """You are an expert database architect and code reviewer. 
Your role is to critically evaluate database schema designs and provide constructive feedback.

You must evaluate the following aspects:

## 1. ENTITY ANALYSIS
- Are all required entities captured from the requirements?
- Are entity names clear and following conventions (PascalCase)?
- Are there any missing entities that are implied but not explicit?
- Are there any unnecessary or redundant entities?

## 2. RELATIONSHIP ANALYSIS  
- Are all relationships correctly identified?
- Are cardinalities (one-to-one, one-to-many, many-to-many) correct?
- Are there missing relationships between entities?
- Are there circular dependencies that could cause issues?

## 3. SCHEMA DESIGN
- Does every table have a proper primary key?
- Are foreign keys correctly defined?
- Are data types appropriate for each column?
- Are NOT NULL constraints applied where needed?
- Are there appropriate default values?

## 4. NORMALIZATION
- Is the schema at least in 3rd Normal Form (3NF)?
- Are there any redundant columns that should be normalized?
- Are there any denormalization decisions that need justification?

## 5. NAMING CONVENTIONS
- Are table names plural and snake_case?
- Are column names snake_case?
- Are foreign key columns named consistently (e.g., entity_id)?
- Are junction tables named appropriately?

## 6. PERFORMANCE CONSIDERATIONS
- Are indexes suggested for frequently queried columns?
- Are indexes suggested for foreign keys?
- Are there any potential N+1 query issues?
- Are large text fields appropriately typed?

## 7. BEST PRACTICES
- Do all tables have created_at and updated_at timestamps?
- Is soft delete implemented if appropriate?
- Are audit fields present if needed?
- Is the schema extensible for future requirements?

## SCORING GUIDELINES
- 9-10: Excellent, production-ready with minor suggestions
- 7-8: Good, needs minor improvements
- 5-6: Acceptable, needs moderate improvements  
- 3-4: Poor, needs significant revision
- 1-2: Critical issues, requires complete redesign

Be specific and actionable in your feedback. Every issue should have a clear recommendation.
"""


def format_schema_for_review(state: GraphState) -> str:
    """Format the current schema state for critic review."""
    
    output = []
    
    # Requirements
    output.append("## ORIGINAL REQUIREMENTS")
    output.append(state['user_requirements'])
    output.append("")
    
    # Entities
    output.append("## EXTRACTED ENTITIES")
    for entity in state.get('entities', []):
        output.append(f"- **{entity['name']}**: {entity['description']}")
        output.append(f"  Attributes: {', '.join(entity['attributes'])}")
    output.append("")
    
    # Relationships
    output.append("## IDENTIFIED RELATIONSHIPS")
    for rel in state.get('relationships', []):
        output.append(f"- {rel['from_entity']} --[{rel['type']}]--> {rel['to_entity']}")
        output.append(f"  {rel['description']}")
    output.append("")
    
    # Tables
    output.append("## DESIGNED TABLES")
    for table in state.get('tables', []):
        output.append(f"\n### Table: {table['name']}")
        output.append(f"Description: {table.get('description', 'N/A')}")
        output.append("Columns:")
        
        for col in table['columns']:
            constraints = []
            if col.get('primary_key'):
                constraints.append("PK")
            if col.get('references'):
                ref = col['references']
                constraints.append(f"FK->{ref['table']}.{ref['column']}")
            if col.get('unique'):
                constraints.append("UNIQUE")
            if not col.get('nullable', True):
                constraints.append("NOT NULL")
            if col.get('default'):
                constraints.append(f"DEFAULT={col['default']}")
            
            constraint_str = f" [{', '.join(constraints)}]" if constraints else ""
            output.append(f"  - {col['name']}: {col['data_type']}{constraint_str}")
        
        if table.get('indexes'):
            output.append("Indexes:")
            for idx in table['indexes']:
                output.append(f"  - {idx.get('name', 'unnamed')}: {', '.join(idx.get('columns', []))}")
    
    return "\n".join(output)


def critic(state: GraphState) -> Dict[str, Any]:
    """
    Critic agent that evaluates the schema design and provides feedback.
    """
    # Start task tracking
    task_updates = start_task(state, "critic")
    
    print("\n" + "🔍" * 20)
    print("CRITIC AGENT EVALUATION")
    print("🔍" * 20)
    
    # Check if we have enough to critique
    if not state.get('tables'):
        print("⚠️ No schema to critique yet, skipping...")
        return {
            **task_updates,
            "current_step": "critic_skipped"
        }
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(CriticEvaluation)
    
    # Format schema for review
    schema_review = format_schema_for_review(state)
    
    # Include previous feedback if this is a revision
    previous_feedback = ""
    if state.get('critic_reports'):
        previous_feedback = "\n\n## PREVIOUS CRITIC FEEDBACK (check if addressed)\n"
        for report in state['critic_reports']:
            for item in report.get('feedback_items', []):
                status = "✅ ADDRESSED" if item.get('applied') else "⏳ PENDING"
                previous_feedback += f"- [{status}] {item['issue']}\n"
    
    messages = [
        SystemMessage(content=CRITIC_SYSTEM_PROMPT),
        HumanMessage(content=f"""Please evaluate this database schema design:

{schema_review}
{previous_feedback}

Provide detailed feedback with specific, actionable recommendations.
Be thorough but fair in your assessment.""")
    ]
    
    try:
        evaluation: CriticEvaluation = structured_llm.invoke(messages)
        
        # Convert to dict format
        feedback_items = [
            {
                "target": item.target,
                "severity": item.severity.value,
                "issue": item.issue,
                "recommendation": item.recommendation,
                "applied": False
            }
            for item in evaluation.feedback_items
        ]
        
        critic_report: CriticReport = {
            "overall_score": evaluation.overall_score,
            "feedback_items": feedback_items,
            "summary": evaluation.summary,
            "requires_revision": evaluation.requires_revision
        }
        
        # Print evaluation results
        print(f"\n📊 OVERALL SCORE: {evaluation.overall_score}/10")
        print(f"📝 SUMMARY: {evaluation.summary}")
        print(f"🔄 REQUIRES REVISION: {'Yes' if evaluation.requires_revision else 'No'}")
        
        if feedback_items:
            print(f"\n📋 FEEDBACK ({len(feedback_items)} items):")
            
            # Group by severity
            critical = [f for f in feedback_items if f['severity'] == 'critical']
            warnings = [f for f in feedback_items if f['severity'] == 'warning']
            suggestions = [f for f in feedback_items if f['severity'] == 'suggestion']
            
            if critical:
                print("\n  🔴 CRITICAL ISSUES:")
                for item in critical:
                    print(f"     • [{item['target']}] {item['issue']}")
                    print(f"       → {item['recommendation']}")
            
            if warnings:
                print("\n  🟡 WARNINGS:")
                for item in warnings:
                    print(f"     • [{item['target']}] {item['issue']}")
                    print(f"       → {item['recommendation']}")
            
            if suggestions:
                print("\n  🟢 SUGGESTIONS:")
                for item in suggestions:
                    print(f"     • [{item['target']}] {item['issue']}")
                    print(f"       → {item['recommendation']}")
        
        # Update critic reports list
        existing_reports = state.get('critic_reports', [])
        updated_reports = existing_reports + [critic_report]
        
        # Complete task
        completion_updates = complete_task(
            {**state, **task_updates},
            "critic",
            f"Score: {evaluation.overall_score}/10, {len(feedback_items)} feedback items, Revision needed: {evaluation.requires_revision}"
        )
        
        return {
            **task_updates,
            **completion_updates,
            "critic_reports": updated_reports,
            "critic_revision_count": state.get('critic_revision_count', 0) + (1 if evaluation.requires_revision else 0),
            "current_step": "critic_complete"
        }
        
    except Exception as e:
        print(f"❌ Critic evaluation failed: {e}")
        
        fail_updates = fail_task(
            {**state, **task_updates},
            "critic",
            str(e)
        )
        
        return {
            **task_updates,
            **fail_updates,
            "current_step": "critic_failed"
        }