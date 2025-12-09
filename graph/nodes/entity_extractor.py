# graph/nodes/entity_extractor.py
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import GraphState, Entity
from utils.llm import get_llm
import json


SYSTEM_PROMPT = """You are a database architect expert. Your task is to extract 
entities from a software requirements description.

For each entity, identify:
1. name: The entity name (singular, PascalCase, e.g., "User", "OrderItem")
2. description: What this entity represents
3. attributes: List of attributes/properties this entity should have

Return your response as a JSON array of entities.

Example output:
[
    {
        "name": "User",
        "description": "A person who uses the system",
        "attributes": ["email", "password", "firstName", "lastName", "createdAt"]
    },
    {
        "name": "Order",
        "description": "A purchase order made by a user",
        "attributes": ["orderNumber", "totalAmount", "status", "orderDate"]
    }
]

Important:
- Include common attributes like id, createdAt, updatedAt (they'll be handled separately)
- Focus on business-specific attributes
- Be thorough - extract ALL entities mentioned or implied
"""


def entity_extractor(state: GraphState) -> Dict[str, Any]:
    """
    Node that extracts entities from user requirements.
    
    Args:
        state: Current graph state
        
    Returns:
        Dictionary with updates to apply to state
    """
    print("\n🔍 Extracting entities from requirements...")
    
    llm = get_llm()
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Extract entities from these requirements:\n\n{state['user_requirements']}")
    ]
    
    response = llm.invoke(messages)
    
    # Parse the JSON response
    try:
        # Clean up response - remove markdown code blocks if present
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        entities = json.loads(content.strip())
        
        print(f"✅ Extracted {len(entities)} entities: {[e['name'] for e in entities]}")
        
        return {
            "entities": entities,
            "current_step": "entity_extraction_complete"
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing entities: {e}")
        return {
            "entities": [],
            "error": f"Failed to parse entities: {e}",
            "current_step": "error"
        }