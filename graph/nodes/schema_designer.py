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
    description: str = Field(default="", max_length=50, description="Max 5 words describing table purpose")
    columns: List[ColumnSchema]
    indexes: List[IndexSchema] = []
    constraints: List[str] = []  # Table-level CHECK constraints
    enable_rls: bool = False  # Row Level Security


class DatabaseSchema(BaseModel):
    tables: List[TableSchema]


SYSTEM_PROMPT = """Design database schema. Be ULTRA-CONCISE. Focus on STRUCTURE ONLY.

REQUIRED on every table:
- id (UUID), created_at, updated_at (TIMESTAMPTZ), deleted_at
- Index EVERY FK column
- Mark PII columns: is_pii=true

Types: TIMESTAMPTZ | DECIMAL | VARCHAR(n) | UUID

Rules:
- Tables: plural_snake_case
- Columns: singular_snake_case  
- Every column needs 'name' + 'data_type'
- Table descriptions: MAX 3 WORDS
- Keep it SIMPLE - refinement will add optimizations later"""


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
            "constraints": table.constraints,
            "row_level_security": table.enable_rls
        })
    return tables


def schema_designer(state: GraphState) -> GraphState:
    start_task(state, "design_schema")
    
    # Use high max_tokens but ultra-concise prompt for initial design
    # Refinement will add detailed optimizations
    llm = get_llm(max_tokens=8192)
    structured_llm = llm.with_structured_output(DatabaseSchema)
    
    context = ContextBuilder.for_schema_design(state)
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context)
    ]
    
    try:
        result = structured_llm.invoke(messages)
        StateManager.increment_llm_calls(state)
        
        # Validate we got tables
        if not result.tables:
            raise ValueError("LLM returned empty tables list")
        
        tables = convert_to_dict(result)
        
        # Double-check we have actual tables
        if not tables:
            raise ValueError("Conversion resulted in empty tables")
        
        state["working"]["tables"] = tables
        state["working"]["current_step"] = "schema_design_complete"
        
        StateManager.save_schema_version(state, "Initial design")
        
        complete_task(state, "design_schema", f"Designed {len(tables)} tables")
        
    except Exception as e:
        from pydantic import ValidationError
        error_msg = str(e)
        
        # Provide detailed error information
        if isinstance(e, ValidationError):
            print(f"   ⚠️  Pydantic Validation Error Details:")
            for err in e.errors()[:3]:  # Show first 3 errors
                print(f"      - {err.get('loc')}: {err.get('msg')}")
            error_msg = f"Schema validation failed: {e.error_count()} errors. "
            error_msg += "LLM output was incomplete or malformed. "
        elif "max_tokens" in error_msg.lower() or "incomplete" in error_msg.lower():
            print(f"   ⚠️  Token limit issue detected - output may be truncated")
            error_msg = "LLM output truncated (max_tokens too low for complex schema). "
        else:
            print(f"   ⚠️  Schema design error: {error_msg[:200]}")
        
        fail_task(state, "design_schema", error_msg)
        state["working"]["tables"] = []
        state["working"]["current_step"] = "error"
    
    return state