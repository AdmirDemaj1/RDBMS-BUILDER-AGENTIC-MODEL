# graph/nodes/validator.py
from ..state import GraphState
from ...utils.task_manager import start_task, complete_task


def validator(state: GraphState) -> GraphState:
    start_task(state, "validate_schema")
    
    working = state["working"]
    tables = working["tables"]
    relationships = working["relationships"]
    
    issues = []
    table_names = [t["name"] for t in tables]
    
    for table in tables:
        # Check PK
        has_pk = any(c.get("primary_key") for c in table["columns"])
        if not has_pk:
            issues.append(f"{table['name']}: no primary key")
        
        # Check timestamps
        col_names = [c["name"] for c in table["columns"]]
        if "created_at" not in col_names:
            issues.append(f"{table['name']}: missing created_at")
        if "updated_at" not in col_names:
            issues.append(f"{table['name']}: missing updated_at")
        
        # Check FK references
        for col in table["columns"]:
            ref = col.get("references")
            if ref and ref.get("table") not in table_names:
                issues.append(f"{table['name']}.{col['name']}: invalid FK reference")
    
    # Check M2M junction tables
    for rel in relationships:
        if rel["type"] == "many-to-many":
            e1, e2 = rel["from_entity"].lower(), rel["to_entity"].lower()
            has_junction = any(
                e1 in t["name"] and e2 in t["name"] or
                f"{e1}_{e2}" in t["name"] or f"{e2}_{e1}" in t["name"]
                for t in tables
            )
            if not has_junction:
                issues.append(f"Missing junction: {rel['from_entity']}<->{rel['to_entity']}")
    
    state["working"]["validation_issues"] = issues
    state["working"]["iteration_count"] += 1
    state["working"]["current_step"] = "validation_complete"
    
    if issues:
        complete_task(state, "validate_schema", f"{len(issues)} issues found")
    else:
        complete_task(state, "validate_schema", f"Valid - {len(tables)} tables OK")
    
    return state