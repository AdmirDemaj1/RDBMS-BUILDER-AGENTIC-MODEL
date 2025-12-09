# graph/nodes/validator.py
from typing import Dict, Any, List
from graph.state import GraphState
from utils.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage
import json


def validator(state: GraphState) -> Dict[str, Any]:
    """
    Node that validates the schema for common issues.
    """
    print("\n✔️  Validating schema...")
    
    issues = []
    tables = state['tables']
    table_names = [t['name'] for t in tables]
    
    for table in tables:
        # Check for primary key
        has_pk = any(col.get('primary_key', False) for col in table['columns'])
        if not has_pk:
            issues.append(f"Table '{table['name']}' has no primary key")
        
        # Check for timestamp columns
        col_names = [col['name'] for col in table['columns']]
        if 'created_at' not in col_names:
            issues.append(f"Table '{table['name']}' missing 'created_at' column")
        if 'updated_at' not in col_names:
            issues.append(f"Table '{table['name']}' missing 'updated_at' column")
        
        # Check foreign key references exist
        for col in table['columns']:
            if col.get('references'):
                ref_table = col['references'].get('table')
                if ref_table and ref_table not in table_names:
                    issues.append(
                        f"Table '{table['name']}' column '{col['name']}' "
                        f"references non-existent table '{ref_table}'"
                    )
    
    # Check for many-to-many junction tables
    for rel in state.get('relationships', []):
        if rel['type'] == 'many-to-many':
            # Look for junction table
            expected_junction = f"{rel['from_entity'].lower()}_{rel['to_entity'].lower()}"
            alt_junction = f"{rel['to_entity'].lower()}_{rel['from_entity'].lower()}"
            
            has_junction = any(
                expected_junction in t['name'] or alt_junction in t['name']
                for t in tables
            )
            if not has_junction:
                issues.append(
                    f"Missing junction table for many-to-many relationship: "
                    f"{rel['from_entity']} <-> {rel['to_entity']}"
                )
    
    if issues:
        print(f"⚠️  Found {len(issues)} issues:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✅ Schema validation passed!")
    
    return {
        "validation_issues": issues,
        "iteration_count": state.get('iteration_count', 0) + 1,
        "current_step": "validation_complete"
    }