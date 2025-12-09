# graph/nodes/erd_generator.py
from typing import Dict, Any, List
from graph.state import GraphState


def generate_mermaid_erd(tables: List[dict], relationships: List[dict]) -> str:
    """
    Generate a Mermaid ERD diagram from tables and relationships.
    """
    lines = ["erDiagram"]
    
    # Generate entity definitions with attributes
    for table in tables:
        table_name = table['name'].upper().replace('_', '-')
        lines.append(f"    {table_name} {{")
        
        for col in table['columns']:
            # Determine key type
            key_marker = ""
            if col.get('primary_key'):
                key_marker = "PK"
            elif col.get('references'):
                key_marker = "FK"
            elif col.get('unique'):
                key_marker = "UK"
            
            # Clean up data type for display
            data_type = col['data_type'].split('(')[0].lower()
            col_name = col['name']
            
            if key_marker:
                lines.append(f"        {data_type} {col_name} {key_marker}")
            else:
                lines.append(f"        {data_type} {col_name}")
        
        lines.append("    }")
    
    lines.append("")
    
    # Generate relationships
    # Build a map of table relationships from foreign keys
    fk_relationships = []
    
    for table in tables:
        table_name = table['name'].upper().replace('_', '-')
        for col in table['columns']:
            if col.get('references'):
                ref_table = col['references']['table'].upper().replace('_', '-')
                fk_relationships.append({
                    'from': ref_table,
                    'to': table_name,
                    'type': 'one-to-many'  # FK implies many side
                })
    
    # Also use the relationships from state for better labeling
    relationship_map = {}
    for rel in relationships:
        key = (rel['from_entity'].lower(), rel['to_entity'].lower())
        relationship_map[key] = rel['type']
        # Also add reverse
        reverse_key = (rel['to_entity'].lower(), rel['from_entity'].lower())
        if rel['type'] == 'one-to-many':
            relationship_map[reverse_key] = 'many-to-one'
        elif rel['type'] == 'many-to-many':
            relationship_map[reverse_key] = 'many-to-many'
        else:
            relationship_map[reverse_key] = rel['type']
    
    # Deduplicate and generate relationship lines
    seen_relationships = set()
    
    for fk_rel in fk_relationships:
        from_table = fk_rel['from']
        to_table = fk_rel['to']
        
        # Skip if we've already added this relationship
        rel_key = tuple(sorted([from_table, to_table]))
        if rel_key in seen_relationships:
            continue
        seen_relationships.add(rel_key)
        
        # Determine cardinality
        # Look up in our relationship map
        from_clean = from_table.lower().replace('-', '_')
        to_clean = to_table.lower().replace('-', '_')
        
        # Try to find matching relationship
        rel_type = 'one-to-many'  # default
        for (e1, e2), rtype in relationship_map.items():
            # Match by checking if entity names are contained in table names
            if (e1 in from_clean or from_clean in e1 + 's') and \
               (e2 in to_clean or to_clean in e2 + 's'):
                rel_type = rtype
                break
            if (e2 in from_clean or from_clean in e2 + 's') and \
               (e1 in to_clean or to_clean in e1 + 's'):
                rel_type = rtype
                break
        
        # Mermaid relationship symbols
        # ||--o{ = one to many
        # ||--|| = one to one  
        # }o--o{ = many to many
        if rel_type == 'one-to-one':
            connector = "||--||"
        elif rel_type == 'many-to-many':
            connector = "}o--o{"
        else:  # one-to-many
            connector = "||--o{"
        
        lines.append(f"    {from_table} {connector} {to_table} : has")
    
    return "\n".join(lines)


def erd_generator(state: GraphState) -> Dict[str, Any]:
    """
    Node that generates a Mermaid ERD diagram from the schema.
    """
    print("\n📊 Generating ERD diagram...")
    
    tables = state.get('tables', [])
    relationships = state.get('relationships', [])
    
    if not tables:
        print("⚠️ No tables to generate ERD from")
        return {
            "erd_diagram": "",
            "current_step": "erd_generation_complete"
        }
    
    mermaid_erd = generate_mermaid_erd(tables, relationships)
    
    print(f"✅ ERD diagram generated with {len(tables)} entities")
    
    return {
        "erd_diagram": mermaid_erd,
        "current_step": "erd_generation_complete"
    }