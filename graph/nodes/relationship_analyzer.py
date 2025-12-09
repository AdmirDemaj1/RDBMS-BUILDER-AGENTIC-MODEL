# graph/nodes/relationship_analyzer.py
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import GraphState, Relationship
from utils.llm import get_llm
import json


SYSTEM_PROMPT = """You are a database architect expert. Given a list of entities 
and the original requirements, identify ALL relationships between entities.

For each relationship, specify:
1. from_entity: The source entity name
2. to_entity: The target entity name  
3. type: One of "one-to-one", "one-to-many", "many-to-many"
4. description: Brief description of the relationship

Return as a JSON array.

Example:
[
    {
        "from_entity": "User",
        "to_entity": "Order",
        "type": "one-to-many",
        "description": "A user can have multiple orders"
    },
    {
        "from_entity": "Order",
        "to_entity": "Product",
        "type": "many-to-many",
        "description": "An order can contain multiple products, a product can be in multiple orders"
    }
]

Guidelines:
- Consider implicit relationships (e.g., if users create orders, there's a relationship)
- For many-to-many, we'll need a junction table later
- Think about ownership, composition, and association relationships
"""


def relationship_analyzer(state: GraphState) -> Dict[str, Any]:
    """
    Node that analyzes relationships between extracted entities.
    """
    print("\n🔗 Analyzing relationships between entities...")
    
    llm = get_llm()
    
    entities_summary = "\n".join([
        f"- {e['name']}: {e['description']} (attributes: {', '.join(e['attributes'])})"
        for e in state['entities']
    ])
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""Original requirements:
{state['user_requirements']}

Extracted entities:
{entities_summary}

Identify all relationships between these entities.""")
    ]
    
    response = llm.invoke(messages)
    
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        relationships = json.loads(content.strip())
        
        print(f"✅ Found {len(relationships)} relationships")
        for rel in relationships:
            print(f"   {rel['from_entity']} --[{rel['type']}]--> {rel['to_entity']}")
        
        return {
            "relationships": relationships,
            "current_step": "relationship_analysis_complete"
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing relationships: {e}")
        return {
            "relationships": [],
            "error": f"Failed to parse relationships: {e}",
            "current_step": "error"
        }