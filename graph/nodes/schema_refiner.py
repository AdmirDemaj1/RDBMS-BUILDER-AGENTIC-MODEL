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
    description: str = Field(default="", max_length=50, description="Max 5 words describing table purpose")
    columns: List[ColumnSchema]
    indexes: List[IndexSchema] = []
    constraints: List[str] = []  # Table-level CHECK constraints
    enable_rls: bool = False


class RefinedSchema(BaseModel):
    tables: List[TableSchema]
    changes_made: List[str] = Field(description="List of changes (max 10 words each)")


REFINER_PROMPT = """Apply critic feedback to optimize the schema. You will receive:
1. Current database schema
2. Critic feedback with specific issues and recommendations
3. Feedback items marked with applied: true/false

YOUR TASK: For each feedback item where applied=true, implement the EXACT change recommended.

## CRITICAL FIXES (Must implement exactly as described)

### Missing Indexes on Foreign Keys:
- Find EVERY column with references_table defined
- Add index entry to table's indexes array: {"name": "idx_{table}_{column}", "columns": ["{column}"], "unique": false, "type": "btree"}
- Verify: Every FK column has a corresponding index

### Missing Audit Columns:
- Check EVERY table for created_at, updated_at, deleted_at
- Add missing columns with correct types: TIMESTAMPTZ NOT NULL DEFAULT NOW() (or NULL for deleted_at)
- Verify: All tables have created_at and updated_at

### Unprotected PII:
- Find ALL columns: email, phone, address, name, first_name, last_name, ssn, birth_date
- Set is_pii: true on these columns
- Verify: All PII columns marked

### Missing UNIQUE Constraints:
- Add unique: true on natural keys (email, license_plate, slug, etc.)
- Verify: Natural keys have unique constraint

### Wrong Data Types:
- TIMESTAMP → TIMESTAMPTZ
- FLOAT/REAL → DECIMAL(p,s) for money
- TEXT → VARCHAR(n) for bounded strings
- Verify: All types are optimal

## PERFORMANCE FIXES
- Add composite indexes for common query patterns (user_id + created_at)
- Add indexes on WHERE/ORDER BY columns (status, type, email)

## SECURITY FIXES
- Enable RLS (enable_rls=true) for multi-tenant/user-data tables
- Add CHECK constraints for status/enum columns
- Set ON DELETE actions for all FKs (CASCADE/RESTRICT/SET NULL)

## VERIFICATION CHECKLIST (Complete before returning)
Before returning the schema, verify:
□ Every foreign key column has a corresponding index in indexes array
□ Every table has created_at, updated_at, and deleted_at columns
□ All PII columns (email, phone, address, name, etc.) have is_pii: true
□ All natural keys have unique: true
□ Status/enum columns have CHECK constraints
□ All timestamps use TIMESTAMPTZ (not TIMESTAMP)
□ All monetary values use DECIMAL (not FLOAT)

## OUTPUT RULES
- Return COMPLETE schema with ALL tables and ALL columns
- Every column needs 'name' and 'data_type'
- Table descriptions: MAX 5 WORDS
- In changes_made, list SPECIFIC changes (e.g., "Added idx_vehicles_company_id index", NOT "Improved indexing")
- List 1 change per line, max 10 words each"""


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
    
    llm = get_llm(max_tokens=6000)  # Increased for complete schema with all fixes applied
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