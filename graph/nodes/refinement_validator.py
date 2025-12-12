# graph/nodes/refinement_validator.py
from typing import List, Dict, Any
from graph.state import GraphState
from utils.task_manager import start_task, complete_task


def verify_refinements(state: GraphState) -> GraphState:
    """
    Programmatically verify that critic feedback was actually applied.
    This runs between refine_schema and critic to catch issues early.
    """
    start_task(state, "verify_refinements")
    
    working = state["working"]
    tables = working.get("tables", [])
    archive = state["archive"]
    
    # Get the latest critic report to check what was supposed to be fixed
    critic_reports = archive.get("critic_reports", [])
    if not critic_reports:
        complete_task(state, "verify_refinements", "No critic report to verify against")
        return state
    
    last_report = critic_reports[-1]
    feedback_items = last_report.get("feedback_items", [])
    
    issues = []
    
    # Check 1: All foreign keys should have indexes
    for table in tables:
        table_name = table["name"]
        indexed_columns = set()
        
        # Collect all indexed columns
        for idx in table.get("indexes", []):
            for col in idx.get("columns", []):
                indexed_columns.add(col)
        
        # Check each FK column has an index
        for col in table.get("columns", []):
            if col.get("references") and col["name"] not in indexed_columns:
                issues.append(f"Missing index on FK: {table_name}.{col['name']}")
    
    # Check 2: All tables should have audit columns
    required_audit_cols = {"created_at", "updated_at"}
    for table in tables:
        table_name = table["name"]
        col_names = {col["name"] for col in table.get("columns", [])}
        
        missing_audit = required_audit_cols - col_names
        if missing_audit:
            issues.append(f"Missing audit columns on {table_name}: {', '.join(missing_audit)}")
    
    # Check 3: PII columns should be marked
    pii_keywords = {"email", "phone", "address", "ssn", "passport", "license",
                    "first_name", "last_name", "full_name", "birth_date", "dob"}
    
    for table in tables:
        table_name = table["name"]
        for col in table.get("columns", []):
            col_name = col["name"].lower()
            # Check if column name contains PII keywords
            if any(keyword in col_name for keyword in pii_keywords):
                if not col.get("is_pii", False):
                    issues.append(f"PII not marked: {table_name}.{col['name']}")
    
    # Check 4: Verify specific feedback was applied
    for feedback in feedback_items:
        if not feedback.get("applied", False):
            continue
        
        issue = feedback.get("issue", "").lower()
        target = feedback.get("target", "")
        
        # Check FK index issues
        if "foreign key" in issue and "index" in issue:
            # Already checked above
            pass
        
        # Check audit column issues
        if "audit" in issue or "created_at" in issue or "updated_at" in issue:
            # Already checked above
            pass
        
        # Check unique constraint issues
        if "unique" in issue and target:
            # Parse target (e.g., "users.email")
            if "." in target:
                table_name, col_name = target.split(".", 1)
                table = next((t for t in tables if t["name"] == table_name), None)
                if table:
                    col = next((c for c in table["columns"] if c["name"] == col_name), None)
                    if col and not col.get("unique", False):
                        issues.append(f"UNIQUE not applied: {target}")
    
    # Store verification results
    working["verification_issues"] = issues
    working["verification_passed"] = len(issues) == 0
    
    if issues:
        print(f"⚠️  VERIFICATION FAILED: {len(issues)} issues found")
        for issue in issues[:5]:  # Show first 5
            print(f"   - {issue}")
        if len(issues) > 5:
            print(f"   ... and {len(issues) - 5} more")
        
        complete_task(state, "verify_refinements", f"Found {len(issues)} unresolved issues")
    else:
        print("✅ VERIFICATION PASSED: All critical fixes applied")
        complete_task(state, "verify_refinements", "All critical fixes verified")
    
    return state


def verify_initial_schema(state: GraphState) -> GraphState:
    """
    Verify the initial schema design has mandatory requirements.
    This runs after schema_designer to catch issues early.
    """
    start_task(state, "verify_initial_schema")
    
    working = state["working"]
    tables = working.get("tables", [])
    
    issues = []
    warnings = []
    
    for table in tables:
        table_name = table["name"]
        columns = table.get("columns", [])
        col_names = {col["name"] for col in columns}
        indexes = table.get("indexes", [])
        indexed_columns = set()
        
        for idx in indexes:
            indexed_columns.update(idx.get("columns", []))
        
        # Check 1: Has primary key
        has_pk = any(col.get("primary_key") for col in columns)
        if not has_pk:
            issues.append(f"{table_name}: Missing primary key")
        
        # Check 2: Has audit columns
        if "created_at" not in col_names:
            issues.append(f"{table_name}: Missing created_at column")
        if "updated_at" not in col_names:
            issues.append(f"{table_name}: Missing updated_at column")
        
        # Check 3: All FKs have indexes
        for col in columns:
            if col.get("references") and col["name"] not in indexed_columns:
                warnings.append(f"{table_name}.{col['name']}: FK without index")
        
        # Check 4: PII columns marked
        pii_keywords = {"email", "phone", "address", "ssn", "passport"}
        for col in columns:
            if any(keyword in col["name"].lower() for keyword in pii_keywords):
                if not col.get("is_pii", False):
                    warnings.append(f"{table_name}.{col['name']}: PII not marked")
    
    # Store results
    working["initial_validation_issues"] = issues
    working["initial_validation_warnings"] = warnings
    
    if issues:
        print(f"⚠️  INITIAL SCHEMA VALIDATION: {len(issues)} critical issues")
        for issue in issues[:3]:
            print(f"   - {issue}")
    
    if warnings:
        print(f"💡 INITIAL SCHEMA WARNINGS: {len(warnings)} warnings")
        for warning in warnings[:3]:
            print(f"   - {warning}")
    
    if not issues and not warnings:
        print("✅ INITIAL SCHEMA: All requirements met")
    
    complete_task(state, "verify_initial_schema", 
                 f"{len(issues)} issues, {len(warnings)} warnings")
    
    return state

