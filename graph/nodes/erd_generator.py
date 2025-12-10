# graph/nodes/erd_generator.py
from typing import List
from graph.state import GraphState
from utils.state_manager import StateManager
from utils.task_manager import start_task, complete_task, fail_task
from datetime import datetime


def generate_mermaid_erd(tables: List[dict]) -> str:
    """Generate enhanced Mermaid ERD with annotations for indexes, PII, and RLS."""
    lines = ["erDiagram"]
    
    for table in tables:
        name = table["name"].upper().replace("_", "-")
        
        # Add table annotations
        annotations = []
        if table.get("row_level_security"):
            annotations.append("🔒RLS")
        
        pii_count = sum(1 for c in table["columns"] if c.get("is_pii"))
        if pii_count:
            annotations.append(f"⚠️PII:{pii_count}")
        
        idx_count = len(table.get("indexes", []))
        if idx_count:
            annotations.append(f"📊IDX:{idx_count}")
        
        table_comment = f"  %% {' '.join(annotations)}" if annotations else ""
        lines.append(f"    {name} {{{table_comment}")
        
        for col in table["columns"][:15]:
            key = ""
            if col.get("primary_key"):
                key = "PK"
            elif col.get("references"):
                key = "FK"
            elif col.get("unique"):
                key = "UK"
            
            # Mark PII columns
            pii_marker = "🔐" if col.get("is_pii") else ""
            
            dtype = col["data_type"].split("(")[0].lower()
            nullable = "" if col.get("nullable", True) else "*"  # * means required
            
            lines.append(f"        {dtype} {col['name']}{nullable} {key}{pii_marker}".rstrip())
        
        if len(table["columns"]) > 15:
            lines.append(f"        ... {len(table['columns']) - 15} more columns")
        
        lines.append("    }")
    
    lines.append("")
    
    # Relationships from FKs with cardinality
    seen = set()
    for table in tables:
        tname = table["name"].upper().replace("_", "-")
        for col in table["columns"]:
            if col.get("references"):
                ref_table = col["references"]["table"].upper().replace("_", "-")
                on_delete = col["references"].get("on_delete", "RESTRICT")
                
                # Create unique key for relationship
                rel_key = (ref_table, tname, col["name"])
                if rel_key not in seen:
                    seen.add(rel_key)
                    
                    # Determine cardinality notation
                    # ||--o{ means one-to-many (one parent, many children)
                    # ||--|| means one-to-one
                    # }o--o{ means many-to-many
                    
                    is_unique_fk = col.get("unique", False)
                    is_nullable = col.get("nullable", True)
                    
                    if is_unique_fk:
                        # One-to-one
                        left = "||"
                        right = "o|" if is_nullable else "||"
                    else:
                        # One-to-many
                        left = "||"
                        right = "o{" if is_nullable else "|{"
                    
                    # Add ON DELETE info for critical relationships
                    rel_label = col["name"].replace("_id", "")
                    if on_delete == "CASCADE":
                        rel_label += " [CASCADE]"
                    
                    lines.append(f"    {ref_table} {left}--{right} {tname} : {rel_label}")
    
    return "\n".join(lines)


def generate_schema_summary(tables: List[dict]) -> str:
    """Generate a text summary of the schema for documentation."""
    lines = [
        "# Schema Summary",
        "",
        f"**Tables:** {len(tables)}",
    ]
    
    total_cols = sum(len(t["columns"]) for t in tables)
    total_indexes = sum(len(t.get("indexes", [])) for t in tables)
    total_fks = sum(1 for t in tables for c in t["columns"] if c.get("references"))
    pii_tables = [t["name"] for t in tables if any(c.get("is_pii") for c in t["columns"])]
    rls_tables = [t["name"] for t in tables if t.get("row_level_security")]
    
    lines.extend([
        f"**Columns:** {total_cols}",
        f"**Indexes:** {total_indexes}",
        f"**Foreign Keys:** {total_fks}",
        "",
        "## Security",
        f"**Tables with PII:** {', '.join(pii_tables) if pii_tables else 'None'}",
        f"**Tables with RLS:** {', '.join(rls_tables) if rls_tables else 'None'}",
        "",
        "## Tables Overview",
    ])
    
    for table in tables:
        pk_col = next((c["name"] for c in table["columns"] if c.get("primary_key")), "id")
        fk_count = sum(1 for c in table["columns"] if c.get("references"))
        idx_count = len(table.get("indexes", []))
        
        lines.append(f"- **{table['name']}** ({len(table['columns'])} cols, {fk_count} FKs, {idx_count} indexes)")
    
    return "\n".join(lines)


def erd_generator(state: GraphState) -> GraphState:
    start_task(state, "generate_erd")
    
    tables = state["working"]["tables"]
    
    if not tables:
        fail_task(state, "generate_erd", "No tables")
        state["working"]["is_complete"] = True
        return state
    
    try:
        # Generate ERD diagram
        erd = generate_mermaid_erd(tables)
        
        # Generate schema summary
        summary = generate_schema_summary(tables)
        
        # Combine ERD with summary as markdown
        full_output = f"""# Entity Relationship Diagram

```mermaid
{erd}
```

{summary}

## Legend
- **PK** = Primary Key
- **FK** = Foreign Key  
- **UK** = Unique Key
- **🔐** = PII (Personal Identifiable Information)
- **🔒RLS** = Row Level Security enabled
- **📊IDX** = Indexed columns
- **\\*** after column name = NOT NULL (required)
- **[CASCADE]** = ON DELETE CASCADE
"""
        
        state["archive"]["erd_diagram"] = full_output
        state["archive"]["completed_at"] = datetime.now().isoformat()
        state["working"]["is_complete"] = True
        state["working"]["current_step"] = "complete"
        
        # Count stats for completion message
        total_indexes = sum(len(t.get("indexes", [])) for t in tables)
        pii_count = sum(1 for t in tables for c in t["columns"] if c.get("is_pii"))
        
        complete_task(
            state, 
            "generate_erd", 
            f"ERD: {len(tables)} tables, {total_indexes} indexes, {pii_count} PII columns"
        )
        
    except Exception as e:
        fail_task(state, "generate_erd", str(e))
        state["working"]["is_complete"] = True
    
    return state