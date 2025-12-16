"""
Response Formatter Agent
Restructures and formats the graph output for optimal frontend display
Uses LLM to intelligently organize and clean the response
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from builder.graph.state import GraphState
from builder.utils.llm import get_llm
from builder.utils.state_manager import StateManager


# ============================================================
# STRUCTURED OUTPUT MODELS
# ============================================================

class TableSummary(BaseModel):
    """Summary of a database table"""
    name: str = Field(description="Table name")
    description: str = Field(description="Brief description of the table's purpose")
    column_count: int = Field(description="Number of columns")
    has_soft_delete: bool = Field(description="Whether table has soft delete (deleted_at)")
    has_timestamps: bool = Field(description="Whether table has created_at/updated_at")
    primary_key: str = Field(description="Primary key column name")
    foreign_keys: List[str] = Field(description="List of foreign key relationships")
    indexes: List[str] = Field(description="List of index names")
    has_rls: bool = Field(description="Whether Row Level Security is enabled")
    has_pii: bool = Field(description="Whether table contains PII data")


class RelationshipSummary(BaseModel):
    """Summary of a table relationship"""
    from_table: str = Field(description="Source table")
    to_table: str = Field(description="Target table")
    relationship_type: str = Field(description="one-to-one, one-to-many, or many-to-many")
    foreign_key: str = Field(description="Foreign key column")
    on_delete: str = Field(description="ON DELETE action (CASCADE, SET NULL, etc.)")


class ModuleSummary(BaseModel):
    """Summary of a NestJS module"""
    name: str = Field(description="Module name without 'Module' suffix")
    description: str = Field(description="What this module handles")
    entities: List[str] = Field(description="Entities managed by this module")
    endpoints: List[str] = Field(description="API endpoints in this module")
    dependencies: List[str] = Field(description="Other modules this depends on")


class EndpointSummary(BaseModel):
    """Summary of an API endpoint"""
    method: str = Field(description="HTTP method (GET, POST, PUT, DELETE)")
    path: str = Field(description="URL path")
    description: str = Field(description="What this endpoint does")
    auth_required: bool = Field(description="Whether authentication is required")
    module: str = Field(description="Which module this belongs to")


class SecuritySummary(BaseModel):
    """Security configuration summary"""
    guards: List[Dict[str, str]] = Field(description="List of guards with name and purpose")
    rls_tables: List[str] = Field(description="Tables with Row Level Security")
    pii_tables: List[str] = Field(description="Tables containing PII data")
    auth_method: str = Field(description="Authentication method (JWT, etc.)")


class FormattedSchema(BaseModel):
    """Formatted database schema for frontend"""
    dialect: str = Field(description="SQL dialect (postgresql, mysql, sqlite)")
    tables: List[TableSummary] = Field(description="List of table summaries")
    relationships: List[RelationshipSummary] = Field(description="Table relationships")
    total_tables: int = Field(description="Total number of tables")
    total_columns: int = Field(description="Total number of columns across all tables")
    total_indexes: int = Field(description="Total number of indexes")
    total_foreign_keys: int = Field(description="Total number of foreign keys")
    ddl_preview: str = Field(description="First 50 lines of DDL as preview")


class FormattedArchitecture(BaseModel):
    """Formatted NestJS architecture for frontend"""
    project_name: str = Field(description="Project name")
    description: str = Field(description="Project description")
    modules: List[ModuleSummary] = Field(description="Module summaries")
    endpoints: List[EndpointSummary] = Field(description="All API endpoints")
    security: SecuritySummary = Field(description="Security configuration")
    environment_variables: List[str] = Field(description="Required environment variables")
    directory_structure: str = Field(description="Project directory structure")
    total_modules: int = Field(description="Total number of modules")
    total_endpoints: int = Field(description="Total number of endpoints")


class FormattedERD(BaseModel):
    """Formatted ERD for frontend"""
    mermaid_diagram: str = Field(description="Clean Mermaid ERD diagram code")
    tables_overview: List[Dict[str, Any]] = Field(description="Quick table overview for UI cards")
    legend: Dict[str, str] = Field(description="Diagram legend explanations")


class FormattedResponse(BaseModel):
    """Complete formatted response for frontend"""
    
    model_config = {"populate_by_name": True}
    
    database_schema: FormattedSchema = Field(description="Formatted database schema", alias="schema")
    architecture: FormattedArchitecture = Field(description="Formatted NestJS architecture")
    erd: FormattedERD = Field(description="Formatted ERD diagram")
    quick_stats: Dict[str, Any] = Field(description="Quick statistics for dashboard display")
    generation_summary: str = Field(description="Human-readable summary of what was generated")


# ============================================================
# FORMATTER AGENT
# ============================================================

def response_formatter(state: GraphState) -> dict:
    """
    Format the graph response for optimal frontend display.
    Uses LLM to intelligently restructure and clean the output.
    """
    print("\n" + "=" * 50)
    print("🎨 RESPONSE FORMATTER")
    print("=" * 50)
    
    archive = state["archive"]
    working = state["working"]
    
    ddl_script = archive.get("ddl_script", "")
    erd_diagram = archive.get("erd_diagram", "")
    nestjs_arch = archive.get("nestjs_architecture", {})
    tables = working.get("tables", [])
    relationships = working.get("relationships", [])
    
    if not ddl_script and not nestjs_arch:
        print("⚠️  No content to format")
        return {}
    
    StateManager.increment_llm_calls(state)
    
    # Build context for LLM
    context = f"""
You are a response formatter agent. Your job is to restructure raw backend generation output into a clean, organized format suitable for frontend display.

## Raw DDL Script (first 100 lines):
```sql
{chr(10).join(ddl_script.split(chr(10))[:100]) if ddl_script else "No DDL generated"}
```

## Raw ERD:
```
{erd_diagram[:2000] if erd_diagram else "No ERD generated"}
```

## Tables Data:
{_format_tables_for_context(tables)}

## Relationships:
{_format_relationships_for_context(relationships)}

## NestJS Architecture:
- Project: {nestjs_arch.get('project_name', 'Unknown')}
- Modules: {len(nestjs_arch.get('modules', []))}
- Endpoints: {len(nestjs_arch.get('endpoints', []))}
- Guards: {nestjs_arch.get('guards', [])}
- Environment Variables: {nestjs_arch.get('environment_variables', [])}

## Your Task:
Analyze this raw output and create a well-structured response with:

1. **Schema Summary**: Clean table summaries with key metadata
2. **Architecture Summary**: Organized module and endpoint information
3. **ERD Summary**: Clean Mermaid diagram and quick overview
4. **Quick Stats**: Dashboard-ready statistics
5. **Generation Summary**: Human-readable paragraph summarizing what was built

Focus on:
- Removing redundant data
- Fixing any formatting issues (like VARCHAR(50)(50) → VARCHAR(50))
- Organizing for easy frontend consumption
- Creating meaningful summaries
- Extracting actionable insights
"""

    # Don't catch exceptions - let LangGraph handle them for proper checkpointing
    # If this fails, the checkpoint will be at the previous node and resume will retry
    # Use higher max_tokens for complex structured output
    llm = get_llm(max_tokens=8192)
    structured_llm = llm.with_structured_output(FormattedResponse)
    
    formatted = structured_llm.invoke(context)
    
    print(f"✅ Formatted response created")
    print(f"   Tables: {formatted.database_schema.total_tables}")
    print(f"   Modules: {formatted.architecture.total_modules}")
    print(f"   Endpoints: {formatted.architecture.total_endpoints}")
    
    # Store formatted response in archive
    # Use by_alias=True to keep "schema" key in JSON output
    # Set is_complete = True since this is the final node before END
    return {
        "archive": {
            "formatted_response": formatted.model_dump(by_alias=True)
        },
        "working": {
            "is_complete": True,
            "current_step": "complete"
        }
    }


def _format_tables_for_context(tables: List[Dict]) -> str:
    """Format tables for LLM context"""
    if not tables:
        return "No tables defined"
    
    lines = []
    for table in tables[:10]:  # Limit to first 10 tables
        cols = [c.get("name", "?") for c in table.get("columns", [])[:5]]
        lines.append(f"- {table.get('name', '?')}: {', '.join(cols)}...")
    
    if len(tables) > 10:
        lines.append(f"... and {len(tables) - 10} more tables")
    
    return "\n".join(lines)


def _format_relationships_for_context(relationships: List[Dict]) -> str:
    """Format relationships for LLM context"""
    if not relationships:
        return "No relationships defined"
    
    lines = []
    for rel in relationships[:10]:
        lines.append(f"- {rel.get('from_entity', '?')} → {rel.get('to_entity', '?')} ({rel.get('type', '?')})")
    
    return "\n".join(lines)


def _create_fallback_format(state: GraphState) -> Dict[str, Any]:
    """Create a basic formatted response without LLM"""
    archive = state["archive"]
    working = state["working"]
    
    tables = working.get("tables", [])
    nestjs = archive.get("nestjs_architecture", {})
    ddl = archive.get("ddl_script", "")
    erd = archive.get("erd_diagram", "")
    
    # Extract Mermaid diagram from ERD
    mermaid = ""
    if "```mermaid" in erd:
        start = erd.find("```mermaid") + 10
        end = erd.find("```", start)
        if end > start:
            mermaid = erd[start:end].strip()
    
    return {
        "schema": {
            "dialect": working.get("sql_dialect", "postgresql"),
            "tables": [
                {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "column_count": len(t.get("columns", [])),
                    "has_soft_delete": any(c.get("name") == "deleted_at" for c in t.get("columns", [])),
                    "has_timestamps": any(c.get("name") in ["created_at", "updated_at"] for c in t.get("columns", [])),
                    "primary_key": next((c.get("name") for c in t.get("columns", []) if c.get("primary_key")), "id"),
                    "foreign_keys": [c.get("name") for c in t.get("columns", []) if c.get("references")],
                    "indexes": [idx.get("name", "") for idx in t.get("indexes", [])],
                    "has_rls": t.get("row_level_security", False),
                    "has_pii": any(c.get("is_pii") for c in t.get("columns", []))
                }
                for t in tables
            ],
            "relationships": [],
            "total_tables": len(tables),
            "total_columns": sum(len(t.get("columns", [])) for t in tables),
            "total_indexes": sum(len(t.get("indexes", [])) for t in tables),
            "total_foreign_keys": sum(1 for t in tables for c in t.get("columns", []) if c.get("references")),
            "ddl_preview": "\n".join(ddl.split("\n")[:50]) if ddl else ""
        },
        "architecture": {
            "project_name": nestjs.get("project_name", "Backend"),
            "description": nestjs.get("description", ""),
            "modules": [
                {
                    "name": m.get("name", "").replace("Module", ""),
                    "description": m.get("description", ""),
                    "entities": m.get("entities", []),
                    "endpoints": [],
                    "dependencies": m.get("dependencies", [])
                }
                for m in nestjs.get("modules", [])
            ],
            "endpoints": [
                {
                    "method": e.get("method", ""),
                    "path": e.get("path", ""),
                    "description": e.get("description", ""),
                    "auth_required": "auth" in e.get("path", "").lower(),
                    "module": _extract_module_from_path(e.get("path", ""))
                }
                for e in nestjs.get("endpoints", [])
            ],
            "security": {
                "guards": [{"name": g, "purpose": "Authentication/Authorization"} for g in nestjs.get("guards", [])],
                "rls_tables": [t.get("name") for t in tables if t.get("row_level_security")],
                "pii_tables": [t.get("name") for t in tables if any(c.get("is_pii") for c in t.get("columns", []))],
                "auth_method": "JWT" if any("jwt" in g.lower() for g in nestjs.get("guards", [])) else "Custom"
            },
            "environment_variables": nestjs.get("environment_variables", []),
            "directory_structure": nestjs.get("directory_structure", ""),
            "total_modules": len(nestjs.get("modules", [])),
            "total_endpoints": len(nestjs.get("endpoints", []))
        },
        "erd": {
            "mermaid_diagram": mermaid,
            "tables_overview": [
                {"name": t.get("name"), "columns": len(t.get("columns", []))}
                for t in tables
            ],
            "legend": {
                "PK": "Primary Key",
                "FK": "Foreign Key",
                "UK": "Unique Key",
                "🔐": "PII Data",
                "🔒RLS": "Row Level Security"
            }
        },
        "quick_stats": {
            "tables": len(tables),
            "modules": len(nestjs.get("modules", [])),
            "endpoints": len(nestjs.get("endpoints", [])),
            "guards": len(nestjs.get("guards", [])),
            "llm_calls": archive.get("total_llm_calls", 0)
        },
        "generation_summary": f"Generated a {working.get('sql_dialect', 'PostgreSQL')} database schema with {len(tables)} tables and a NestJS backend with {len(nestjs.get('modules', []))} modules and {len(nestjs.get('endpoints', []))} API endpoints."
    }


def _extract_module_from_path(path: str) -> str:
    """Extract module name from API path"""
    parts = path.strip("/").split("/")
    if len(parts) >= 2:
        return parts[1].replace("-", " ").title()
    return "Root"

