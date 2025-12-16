# graph/nodes/entity_extractor.py
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from ..state import GraphState
from ...utils.llm import get_llm
from ...utils.state_manager import StateManager
from ...utils.context_builder import ContextBuilder
from ...utils.task_manager import start_task, complete_task, fail_task
from pydantic import BaseModel, Field


class EntitySchema(BaseModel):
    name: str
    description: str
    attributes: List[str]


class EntitiesResult(BaseModel):
    entities: List[EntitySchema]


SYSTEM_PROMPT = """Extract database entities from requirements.

Include:
- Business objects (User, Order, Product)
- Junction entities for M:N relationships (OrderItem, Enrollment)
- Lookup tables (Category, Status)

Exclude: Simple attributes, actions/verbs, UI concepts, derived data

Format:
- name: PascalCase, singular (User, OrderItem)
- description: 1-2 sentences on purpose
- attributes: Business fields only (no id, timestamps)

Ensure: No duplicates, junction tables identified, hierarchies captured."""


def entity_extractor(state: GraphState) -> GraphState:
    start_task(state, "extract_entities")
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(EntitiesResult)
    
    context = ContextBuilder.for_entity_extraction(state)
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context)
    ]
    
    try:
        result = structured_llm.invoke(messages)
        StateManager.increment_llm_calls(state)
        
        entities = [
            {"name": e.name, "description": e.description, "attributes": e.attributes}
            for e in result.entities
        ]
        
        state["working"]["entities"] = entities
        state["working"]["current_step"] = "entity_extraction_complete"
        
        names = [e["name"] for e in entities]
        complete_task(state, "extract_entities", f"Extracted {len(entities)}: {', '.join(names[:5])}")
        
    except Exception as e:
        fail_task(state, "extract_entities", str(e))
        # Re-raise to let LangGraph checkpoint at previous node for proper resume
        raise
    
    return state