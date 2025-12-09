# graph/nodes/schema_designer.py
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import GraphState
from utils.llm import get_llm
from pydantic import BaseModel, Field
import json


# Define Pydantic models for structured output
class ColumnSchema(BaseModel):
    name: str = Field(description="Column name in snake_case")
    data_type: str = Field(description="PostgreSQL data type")
    nullable: bool = Field(default=True)
    primary_key: bool = Field(default=False)
    unique: bool = Field(default=False)
    default: Optional[str] = Field(default=None)
    references_table: Optional[str] = Field(default=None, description="Referenced table for FK")
    references_column: Optional[str] = Field(default=None, description="Referenced column for FK")


class TableSchema(BaseModel):
    name: str = Field(description="Table name in snake_case, plural")
    description: str = Field(description="Brief description")
    columns: List[ColumnSchema] = Field(description="List of columns")


class DatabaseSchema(BaseModel):
    tables: List[TableSchema] = Field(description="List of all tables")


SYSTEM_PROMPT = """You are a database architect expert. Convert entities and 
relationships into a proper relational database schema.

Rules:
1. Every table MUST have: id (UUID PRIMARY KEY), created_at (TIMESTAMP), updated_at (TIMESTAMP)
2. For one-to-many: add foreign key column to the "many" side
3. For many-to-many: create a junction table
4. Use appropriate PostgreSQL data types
5. Table names: snake_case, plural (e.g., users, order_items)
6. Column names: snake_case

Return a valid JSON object with a "tables" array.
"""


def clean_json_response(content: str) -> str:
    """Clean and extract JSON from LLM response."""
    content = content.strip()
    
    # Remove markdown code blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        parts = content.split("```")
        if len(parts) >= 2:
            content = parts[1]
    
    return content.strip()


def parse_schema_response(response_content: str) -> DatabaseSchema:
    """Parse the LLM response into a DatabaseSchema object."""
    
    # If it's already a dict/list (structured output worked), wrap it
    if isinstance(response_content, dict):
        return DatabaseSchema(**response_content)
    
    if isinstance(response_content, list):
        return DatabaseSchema(tables=response_content)
    
    # Otherwise, it's a string - parse the JSON
    cleaned = clean_json_response(response_content)
    
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Try to fix common issues
        # Sometimes the response is just an array
        if cleaned.startswith('['):
            data = {"tables": json.loads(cleaned)}
        else:
            raise e
    
    # Handle if the response is just an array of tables
    if isinstance(data, list):
        data = {"tables": data}
    
    return DatabaseSchema(**data)


def convert_to_dict_format(schema: DatabaseSchema) -> List[dict]:
    """Convert Pydantic model to the dict format expected by other nodes."""
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
    return tables


def schema_designer(state: GraphState) -> Dict[str, Any]:
    """
    Node that designs the database schema from entities and relationships.
    """
    print("\n📐 Designing database schema...")
    
    llm = get_llm()
    
    entities_summary = "\n".join([
        f"- {e['name']}: {e['description']} (attributes: {', '.join(e['attributes'])})"
        for e in state['entities']
    ])
    
    relationships_summary = "\n".join([
        f"- {r['from_entity']} --[{r['type']}]--> {r['to_entity']}"
        for r in state['relationships']
    ])
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""Design a complete database schema.

ENTITIES:
{entities_summary}

RELATIONSHIPS:
{relationships_summary}

Create ALL tables needed including junction tables for many-to-many relationships.
Return as JSON with a "tables" array.""")
    ]
    
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            # Try with structured output first
            try:
                structured_llm = llm.with_structured_output(DatabaseSchema)
                result = structured_llm.invoke(messages)
                
                # Check if result is already a DatabaseSchema
                if isinstance(result, DatabaseSchema):
                    schema = result
                else:
                    # It might be a string or dict, parse it
                    schema = parse_schema_response(result)
                    
            except Exception as structured_error:
                print(f"⚠️  Structured output failed, falling back to raw parsing: {structured_error}")
                
                # Fallback: get raw response and parse manually
                response = llm.invoke(messages)
                schema = parse_schema_response(response.content)
            
            tables = convert_to_dict_format(schema)
            
            print(f"✅ Designed {len(tables)} tables:")
            for table in tables:
                col_count = len(table.get('columns', []))
                print(f"   📋 {table['name']} ({col_count} columns)")
            
            return {
                "tables": tables,
                "current_step": "schema_design_complete"
            }
            
        except Exception as e:
            print(f"⚠️  Attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                # Add clarification for retry
                messages.append(HumanMessage(
                    content="Please return ONLY a valid JSON object with this exact structure: {\"tables\": [...]}. No markdown, no explanation."
                ))
            else:
                print(f"❌ Error designing schema after {max_retries} attempts: {e}")
                return {
                    "tables": [],
                    "error": f"Failed to design schema: {e}",
                    "current_step": "error"
                }