# graph/nodes/relationship_analyzer.py
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import GraphState
from ...utils.llm import get_llm
from ...utils.state_manager import StateManager
from ...utils.context_builder import ContextBuilder
from ...utils.task_manager import start_task, complete_task, fail_task
from pydantic import BaseModel, Field
from enum import Enum


class RelType(str, Enum):
    ONE_TO_ONE = "one-to-one"
    ONE_TO_MANY = "one-to-many"
    MANY_TO_ONE = "many-to-one"  # Will be normalized to one-to-many with swapped entities
    MANY_TO_MANY = "many-to-many"


class RelationshipSchema(BaseModel):
    from_entity: str
    to_entity: str
    type: RelType
    description: str


class RelationshipsResult(BaseModel):
    relationships: List[RelationshipSchema]


SYSTEM_PROMPT = """Identify relationships between entities.

Types:
- one-to-one: User↔Profile (FK on dependent side)
- one-to-many: User→Orders (FK on "many" side)  
- many-to-many: Students↔Courses (needs junction table)

For each relationship:
- from_entity: The "one" side (exact entity name)
- to_entity: The related entity (exact entity name)
- type: one-to-one, one-to-many, or many-to-many
- description: Brief business meaning

Check for: Self-references (Category→parent), hierarchies, implicit relationships.
Every entity should have at least one relationship."""


def relationship_analyzer(state: GraphState) -> GraphState:
    start_task(state, "analyze_relationships")
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(RelationshipsResult)
    
    context = ContextBuilder.for_relationship_analysis(state)
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context)
    ]
    
    try:
        result = structured_llm.invoke(messages)
        StateManager.increment_llm_calls(state)
        
        relationships = []
        for r in result.relationships:
            # Normalize many-to-one to one-to-many by swapping entities
            if r.type == RelType.MANY_TO_ONE:
                relationships.append({
                    "from_entity": r.to_entity,  # Swap
                    "to_entity": r.from_entity,  # Swap
                    "type": "one-to-many",       # Normalize
                    "description": r.description
                })
            else:
                relationships.append({
                    "from_entity": r.from_entity,
                    "to_entity": r.to_entity,
                    "type": r.type.value,
                    "description": r.description
                })
        
        state["working"]["relationships"] = relationships
        state["working"]["current_step"] = "relationship_analysis_complete"
        
        complete_task(state, "analyze_relationships", f"Found {len(relationships)} relationships")
        
    except Exception as e:
        fail_task(state, "analyze_relationships", str(e))
        state["working"]["relationships"] = []
        state["working"]["current_step"] = "error"
    
    return state