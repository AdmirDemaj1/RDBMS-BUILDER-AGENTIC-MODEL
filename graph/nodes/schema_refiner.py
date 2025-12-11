# graph/nodes/schema_refiner.py
from typing import List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import GraphState
from utils.llm import get_llm
from utils.state_manager import StateManager
from utils.context_builder import ContextBuilder
from utils.task_manager import start_task, complete_task, fail_task
from pydantic import BaseModel, Field


class IndexSchema(BaseModel):
    name: str
    columns: List[str]
    unique: bool = False
    type: str = "btree"


class ColumnSchema(BaseModel):
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False
    default: Optional[str] = None
    references_table: Optional[str] = None
    references_column: Optional[str] = None
    on_delete: Optional[str] = None
    check_constraint: Optional[str] = None
    is_pii: bool = False


class TableSchema(BaseModel):
    name: str
    description: str
    columns: List[ColumnSchema]
    indexes: List[IndexSchema] = []
    constraints: List[str] = []  # Table-level CHECK constraints
    enable_rls: bool = False


class RefinedSchema(BaseModel):
    tables: List[TableSchema]
    changes_made: List[str]


REFINER_PROMPT = """Apply critic feedback to create a production-optimized schema.

## Column Definitions
CRITICAL: Every column MUST have both 'name' and 'data_type' fields defined.
NEVER create a column entry with only a constraint - use the table's 'constraints' array instead.

## Priority Order
1. CRITICAL issues (must fix)
2. Performance issues (indexes, types)
3. Security issues (PII, RLS, constraints)
4. WARNING issues
5. SUGGESTIONS

## Performance Fixes
- Add index for EVERY FK column: idx_{table}_{column}
- Add indexes for columns in WHERE/ORDER BY (status, created_at, email)
- Use composite indexes for common patterns (user_id + created_at)
- Use TIMESTAMPTZ instead of TIMESTAMP
- Use appropriate VARCHAR lengths

## Security Fixes
- Mark PII columns (is_pii=true): email, phone, address, name, ssn, ip_address
- Enable RLS (enable_rls=true) for multi-tenant or user-data tables
- Add CHECK constraints for status/enum columns
- Specify ON DELETE action for all FKs (CASCADE, RESTRICT, SET NULL)

## Constraints
- Column-level constraints: use check_constraint field on the column (e.g., "age > 0")
- Table-level constraints: use the table's constraints array (e.g., "end_date >= start_date")
- NEVER add a column entry that only contains a constraint without name/data_type

## Integrity Fixes
- Add NOT NULL on required fields
- Add UNIQUE on natural keys
- Add missing standard columns (id, created_at, updated_at)
- Fix FK types to match referenced PK

## Rules
- Return COMPLETE schema with ALL tables
- Preserve working relationships
- List each change with clear description
- Do NOT remove tables/columns unless explicitly requested"""


def convert_to_dict(schema: RefinedSchema) -> tuple:
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
                "check_constraint": col.check_constraint,
                "is_pii": col.is_pii,
                "is_encrypted": False,
            }
            if col.references_table and col.references_column:
                col_dict["references"] = {
                    "table": col.references_table,
                    "column": col.references_column,
                    "on_delete": col.on_delete or "RESTRICT"
                }
            columns.append(col_dict)
        
        indexes = [
            {
                "name": idx.name,
                "columns": idx.columns,
                "unique": idx.unique,
                "type": idx.type
            }
            for idx in table.indexes
        ]
        
        tables.append({
            "name": table.name,
            "description": table.description,
            "columns": columns,
            "indexes": indexes,
            "constraints": table.constraints,
            "row_level_security": table.enable_rls
        })
    
    return tables, schema.changes_made


def schema_refiner(state: GraphState) -> GraphState:
    start_task(state, "refine_schema")
    
    working = state["working"]
    
    print("\n🔧 SCHEMA REFINER")
    
    summary = working.get("critic_summary")
    if not summary or not summary.get("requires_revision"):
        complete_task(state, "refine_schema", "No revision needed")
        return state
    
    pending = StateManager.get_pending_feedback(state)
    if not pending:
        complete_task(state, "refine_schema", "No pending feedback")
        return state
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(RefinedSchema)
    
    context = ContextBuilder.for_refiner(state)
    
    messages = [
        SystemMessage(content=REFINER_PROMPT),
        HumanMessage(content=context)
    ]
    
    try:
        result = structured_llm.invoke(messages)
        StateManager.increment_llm_calls(state)
        
        tables, changes = convert_to_dict(result)
        
        print(f"   Changes: {len(changes)}")
        for change in changes[:3]:
            print(f"   - {change[:60]}")
        
        state["working"]["tables"] = tables
        state["working"]["current_step"] = "refine_complete"
        
        StateManager.mark_feedback_applied(state)
        StateManager.save_schema_version(state, f"Refined: {len(changes)} changes")
        
        complete_task(state, "refine_schema", f"Applied {len(changes)} improvements")
        
    except Exception as e:
        from pydantic import ValidationError
        error_msg = str(e)
        
        # Provide more detailed error for validation issues
        if isinstance(e, ValidationError):
            error_msg = f"Schema validation failed: {e.error_count()} errors. "
            error_msg += "LLM may have returned malformed column definitions. "
            error_msg += "Check that all columns have 'name' and 'data_type' fields."
        
        fail_task(state, "refine_schema", error_msg)
        state["working"]["current_step"] = "refine_failed"
    
    return state