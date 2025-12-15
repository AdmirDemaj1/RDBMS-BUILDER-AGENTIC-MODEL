# graph/nodes/intent_classifier.py
"""
Intent Classifier Node

Determines if user input is related to software development and database design.
"""

from ..state import GraphState
from ...utils.llm import get_llm
from ...utils.state_manager import StateManager
from ...utils.task_manager import create_task, start_task, complete_task
from pydantic import BaseModel, Field
from typing import Literal


class IntentClassification(BaseModel):
    """Classification of user intent."""
    is_relevant: bool = Field(description="Whether the input is related to software development, database design, or system architecture")
    intent_type: Literal["new_project", "modification", "question", "explanation", "unrelated"] = Field(
        description="Type of intent: new_project (new system), modification (change existing), question (ask about output), explanation (explain something), unrelated (off-topic)"
    )
    reasoning: str = Field(description="Brief explanation of the classification")
    suggested_action: str = Field(description="What the system should do next")


def intent_classifier(state: GraphState) -> dict:
    """
    Classify user intent and determine if it's related to software development.
    
    This node acts as a gatekeeper and router for the conversation.
    """
    working = state["working"]
    archive = state["archive"]
    
    task_id = create_task(state, "intent_classifier", "Analyzing user intent")
    start_task(state, task_id)
    
    user_input = working["user_requirements"]
    
    # Check if we have previous context
    has_previous_output = bool(archive.get("ddl_script") or archive.get("nestjs_architecture"))
    previous_entities = working.get("entities", [])
    previous_tables = working.get("tables", [])
    
    # Build context-aware prompt
    context = ""
    if has_previous_output:
        context = f"""
Previous Context:
- Database schema has been generated ({len(previous_tables)} tables)
- Entities: {', '.join([e.get('name', '') for e in previous_entities[:5]])}
- NestJS architecture has been generated: {bool(archive.get("nestjs_architecture"))}

The user may be asking questions about the previously generated output or requesting modifications.
"""
    
    prompt = f"""You are an AI assistant that helps with software development, database design, and system architecture.

Analyze the following user input and determine:
1. Is it related to software development, databases, or system architecture?
2. What is the user trying to do?

{context}

User Input: "{user_input}"

Classify the intent and provide guidance."""
    
    try:
        llm = get_llm()
        StateManager.increment_llm_calls(state)
        
        structured_llm = llm.with_structured_output(IntentClassification)
        classification = structured_llm.invoke(prompt)
        
        # Store classification in working state
        result = {
            "working": {
                "current_step": "intent_classification",
                "intent_classification": {
                    "is_relevant": classification.is_relevant,
                    "intent_type": classification.intent_type,
                    "reasoning": classification.reasoning,
                    "suggested_action": classification.suggested_action
                }
            }
        }
        
        complete_task(state, task_id, f"Intent: {classification.intent_type} - {classification.reasoning[:50]}...")
        
        return result
        
    except Exception as e:
        from utils.task_manager import fail_task
        fail_task(state, task_id, str(e))
        return {
            "working": {
                "error": f"Intent classification failed: {str(e)}",
                "intent_classification": {
                    "is_relevant": False,
                    "intent_type": "unrelated",
                    "reasoning": "Error during classification",
                    "suggested_action": "Ask user to rephrase"
                }
            }
        }


def should_proceed_with_generation(state: GraphState) -> str:
    """Routing function based on intent classification."""
    classification = state["working"].get("intent_classification", {})
    
    if not classification.get("is_relevant", False):
        return "unrelated"
    
    intent_type = classification.get("intent_type", "")
    
    if intent_type in ["new_project", "modification"]:
        return "generate"
    elif intent_type in ["question", "explanation"]:
        return "answer"
    else:
        return "clarify"

