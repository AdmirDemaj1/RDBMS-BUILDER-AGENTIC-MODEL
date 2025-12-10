# graph/nodes/schema_refiner.py
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import GraphState, CriticFeedback
from utils.llm import get_llm
from utils.task_manager import start_task, complete_task, fail_task
from pydantic import BaseModel, Field
import json


class ColumnSchema(BaseModel):
    name: str = Field(description="Column name in snake_case")
    data_type: str = Field(description="PostgreSQL data type")
    nullable: bool = Field(default=True)
    primary_key: bool = Field(default=False)
    unique: bool = Field(default=False)
    default: Optional[str] = Field(default=None)
    references_table: Optional[str] = Field(default=None)
    references_column: Optional[str] = Field(default=None)


class TableSchema(BaseModel):
    name: str = Field(description="Table name in snake_case, plural")
    description: str = Field(description="Brief description")
    columns: List[ColumnSchema] = Field(description="List of columns")


class RefinedSchema(BaseModel):
    tables: List[TableSchema] = Field(description="List of all refined tables")
    changes_made: List[str] = Field(description="List of changes made based on feedback")


REFINER_SYSTEM_PROMPT = """You are an expert database architect tasked with improving a database schema based on critic feedback.

Your job is to:
1. Review each piece of feedback carefully
2. Apply the recommended fixes where appropriate
3. Maintain consistency across all changes
4. Document what changes you made

IMPORTANT RULES:
- Always maintain referential integrity
- Keep existing functionality while improving
- Apply naming conventions consistently
- Ensure all tables have id, created_at, updated_at
- Add appropriate indexes for foreign keys
- Fix any normalization issues

Return the complete improved schema with ALL tables (not just changed ones).
"""


def convert_to_dict_format(schema: RefinedSchema) -> tuple[List[dict], List[str]]:
    """Convert Pydantic model to dict format."""
    tables = []
    for table in schema.tables:
        columns = []
        for col in table.columns:
            col_dict = {
                "name": col.name,
                "data_type": col.data_type,
                "nullable": col.nullable,
                "primary_key": col.primary_key,
                "unique": col.unique,
                "default": col.default,
            }
            if col.references_table and col.references_column:
                col_dict["references"] = {
                    "table": col.references_table,
                    "column": col.references_column
                }
            columns.append(col_dict)
        
        tables.append({
            "name": table.name,
            "description": table.description,
            "columns": columns,
            "indexes": []
        })
    
    return tables, schema.changes_made


def format_current_schema(tables: List[dict]) -> str:
    """Format current schema for the refiner."""
    output = []
    
    for table in tables:
        output.append(f"\n### {table['name']}")
        output.append(f"Description: {table.get('description', 'N/A')}")
        
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
            
            constraint_str = f" [{', '.join(constraints)}]" if constraints else ""
            output.append(f"  - {col['name']}: {col['data_type']}{constraint_str}")
    
    return "\n".join(output)


def format_feedback(critic_reports: List[dict]) -> str:
    """Format critic feedback for the refiner."""
    output = ["## CRITIC FEEDBACK TO ADDRESS\n"]
    
    # Get the latest report
    if not critic_reports:
        return "No feedback to address."
    
    latest_report = critic_reports[-1]
    
    # Prioritize by severity
    feedback_items = latest_report.get('feedback_items', [])
    
    critical = [f for f in feedback_items if f['severity'] == 'critical' and not f.get('applied')]
    warnings = [f for f in feedback_items if f['severity'] == 'warning' and not f.get('applied')]
    suggestions = [f for f in feedback_items if f['severity'] == 'suggestion' and not f.get('applied')]
    
    if critical:
        output.append("### 🔴 CRITICAL (Must Fix):")
        for item in critical:
            output.append(f"- **{item['target']}**: {item['issue']}")
            output.append(f"  Recommendation: {item['recommendation']}")
    
    if warnings:
        output.append("\n### 🟡 WARNINGS (Should Fix):")
        for item in warnings:
            output.append(f"- **{item['target']}**: {item['issue']}")
            output.append(f"  Recommendation: {item['recommendation']}")
    
    if suggestions:
        output.append("\n### 🟢 SUGGESTIONS (Nice to Have):")
        for item in suggestions:
            output.append(f"- **{item['target']}**: {item['issue']}")
            output.append(f"  Recommendation: {item['recommendation']}")
    
    return "\n".join(output)


def schema_refiner(state: GraphState) -> Dict[str, Any]:
    """
    Node that refines the schema based on critic feedback.
    """
    # Start task tracking
    task_updates = start_task(state, "refine_schema")
    
    print("\n" + "🔧" * 20)
    print("SCHEMA REFINER")
    print("🔧" * 20)
    
    # Check if we have feedback to address
    if not state.get('critic_reports'):
        print("⚠️ No critic feedback to address")
        return {
            **task_updates,
            "current_step": "refine_skipped"
        }
    
    latest_report = state['critic_reports'][-1]
    
    if not latest_report.get('requires_revision'):
        print("✅ No revision required, schema is good!")
        return {
            **task_updates,
            "current_step": "refine_skipped"
        }
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(RefinedSchema)
    
    # Format inputs
    current_schema = format_current_schema(state['tables'])
    feedback = format_feedback(state['critic_reports'])
    
    # Include entities and relationships for context
    entities_str = "\n".join([
        f"- {e['name']}: {e['description']}"
        for e in state.get('entities', [])
    ])
    
    relationships_str = "\n".join([
        f"- {r['from_entity']} --[{r['type']}]--> {r['to_entity']}"
        for r in state.get('relationships', [])
    ])
    
    messages = [
        SystemMessage(content=REFINER_SYSTEM_PROMPT),
        HumanMessage(content=f"""Please improve this database schema based on the critic feedback.

## ORIGINAL REQUIREMENTS
{state['user_requirements']}

## ENTITIES
{entities_str}

## RELATIONSHIPS
{relationships_str}

## CURRENT SCHEMA
{current_schema}

{feedback}

Return the complete improved schema with all changes applied.
Document each change you make in the changes_made list.""")
    ]
    
    try:
        result: RefinedSchema = structured_llm.invoke(messages)
        
        tables, changes_made = convert_to_dict_format(result)
        
        # Print changes
        print(f"\n📝 CHANGES MADE ({len(changes_made)}):")
        for change in changes_made:
            print(f"   ✓ {change}")
        
        # Mark feedback as applied
        updated_reports = []
        for report in state['critic_reports']:
            updated_report = report.copy()
            updated_feedback = []
            for item in report.get('feedback_items', []):
                updated_item = item.copy()
                updated_item['applied'] = True
                updated_feedback.append(updated_item)
            updated_report['feedback_items'] = updated_feedback
            updated_reports.append(updated_report)
        
        # Complete task
        completion_updates = complete_task(
            {**state, **task_updates},
            "refine_schema",
            f"Applied {len(changes_made)} improvements to {len(tables)} tables"
        )
        
        return {
            **task_updates,
            **completion_updates,
            "tables": tables,
            "critic_reports": updated_reports,
            "current_step": "refine_complete"
        }
        
    except Exception as e:
        print(f"❌ Schema refinement failed: {e}")
        
        fail_updates = fail_task(
            {**state, **task_updates},
            "refine_schema",
            str(e)
        )
        
        return {
            **task_updates,
            **fail_updates,
            "current_step": "refine_failed"
        }