# graph/nodes/schema_designer.py
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
    type: str = "btree"  # btree, hash, gin, gist


class ColumnSchema(BaseModel):
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False
    default: Optional[str] = None
    references_table: Optional[str] = None
    references_column: Optional[str] = None
    on_delete: Optional[str] = None  # CASCADE, SET NULL, RESTRICT
    check_constraint: Optional[str] = None
    is_pii: bool = False  # Personal Identifiable Information


class TableSchema(BaseModel):
    name: str
    description: str
    columns: List[ColumnSchema]
    indexes: List[IndexSchema] = []
    enable_rls: bool = False  # Row Level Security


class DatabaseSchema(BaseModel):
    tables: List[TableSchema]


SYSTEM_PROMPT = """Design a production-grade, optimized database schema.

## STRUCTURE
Every table MUST have: id (UUID PK DEFAULT gen_random_uuid()), created_at (TIMESTAMPTZ DEFAULT NOW()), updated_at (TIMESTAMPTZ DEFAULT NOW())

Naming: tables=plural snake_case, columns=singular snake_case, FKs={table_singular}_id

## OPTIMIZATION
Indexes (CRITICAL for performance):
- Primary keys are auto-indexed
- Add indexes on ALL foreign keys (idx_{table}_{column})
- Add indexes on columns used in WHERE/ORDER BY (status, created_at, email)
- Use composite indexes for common query patterns (user_id + created_at)
- Use UNIQUE indexes for natural keys
- Consider partial indexes for filtered queries (WHERE status = 'active')

Data Types (choose optimal):
- UUID for PKs (distributed-safe), BIGSERIAL for high-insert tables
- VARCHAR(n) with appropriate limits (email:255, phone:20, slug:100)
- TEXT only for truly unbounded content
- TIMESTAMPTZ (not TIMESTAMP) for timezone-aware dates
- DECIMAL(12,2) for money, NEVER use FLOAT
- JSONB for flexible data (with GIN index if queried)
- Use enums or CHECK constraints for status fields

## SECURITY
Mark PII columns (is_pii=true): email, phone, address, ssn, ip_address, name
Enable Row Level Security (enable_rls=true) for: multi-tenant tables, user data
Add CHECK constraints for data validation (age > 0, status IN ('active','inactive'))

## RELATIONSHIPS
- 1:N → FK on "many" side with ON DELETE action (CASCADE for owned data, RESTRICT for references)
- M:N → junction table with composite PK or id + unique constraint
- 1:1 → FK + UNIQUE on dependent side
- Self-references → nullable FK (parent_id)

## BEST PRACTICES
- Soft delete: add deleted_at TIMESTAMPTZ column instead of hard delete
- Versioning: add version INTEGER DEFAULT 1 for optimistic locking
- Audit: consider created_by/updated_by UUID references to users
- Denormalize carefully: only for proven read-heavy patterns

Output complete schema with indexes for every FK and common query columns."""


def convert_to_dict(schema: DatabaseSchema) -> List[dict]:
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
            "constraints": [],
            "row_level_security": table.enable_rls
        })
    return tables


def schema_designer(state: GraphState) -> GraphState:
    start_task(state, "design_schema")
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(DatabaseSchema)
    
    context = ContextBuilder.for_schema_design(state)
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context)
    ]
    
    try:
        result = structured_llm.invoke(messages)
        StateManager.increment_llm_calls(state)
        
        tables = convert_to_dict(result)
        
        state["working"]["tables"] = tables
        state["working"]["current_step"] = "schema_design_complete"
        
        StateManager.save_schema_version(state, "Initial design")
        
        complete_task(state, "design_schema", f"Designed {len(tables)} tables")
        
    except Exception as e:
        fail_task(state, "design_schema", str(e))
        state["working"]["tables"] = []
        state["working"]["current_step"] = "error"
    
    return state