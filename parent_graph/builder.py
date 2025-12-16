"""
Parent Graph Builder
Orchestrates Backend Builder and Explainer subgraphs

The parent graph uses an LLM to route user requests to the appropriate subgraph:
- Backend Builder: For building/modifying backends
- Explainer: For explaining the generated backend

Each subgraph handles its own logic including user interaction.
"""
from typing import Optional, Callable, Any, Dict, Literal
from datetime import datetime
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from parent_graph.state import (
    ParentGraphState,
    WorkflowMode,
    SubgraphStatus,
    SubgraphExecution
)

# Import subgraphs
from main import run_builder
from explainer.run_explainer import run_explainer
from builder.utils.llm import get_llm
from builder.utils.checkpoint_manager import CheckpointerType


# ============================================================
# INTENT CLASSIFICATION
# ============================================================

class IntentClassification(BaseModel):
    """Classification of user intent for routing."""
    intent: Literal["build", "explain"] = Field(
        description="'build' for creating/modifying backend, 'explain' for questions about generated backend"
    )
    reasoning: str = Field(description="Brief explanation of why this intent was chosen")


def classify_intent(user_input: str, has_backend: bool = False) -> IntentClassification:
    """
    Use LLM to classify user intent for routing.
    
    Args:
        user_input: The user's request
        has_backend: Whether a backend has already been generated
    
    Returns:
        IntentClassification with intent type and reasoning
    """
    context = ""
    if has_backend:
        context = "Note: A backend has already been generated. The user may be asking about it."
    
    prompt = f"""Classify the user's intent into one of two categories:

1. "build" - User wants to CREATE or MODIFY a backend system. Examples:
   - "Build a hotel management system"
   - "Create an e-commerce backend"
   - "Add a payment module to the system"
   - "Modify the user table to add email verification"

2. "explain" - User wants to UNDERSTAND or get INFORMATION about an existing backend. Examples:
   - "Explain the backend you generated"
   - "What tables are in the database?"
   - "How does the user authentication work?"
   - "Describe the relationships between entities"
   - "What endpoints are available?"

{context}

User Input: "{user_input}"

Classify this intent."""

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(IntentClassification)
        result = structured_llm.invoke(prompt)
        return result
    except Exception as e:
        # Default to build if classification fails
        return IntentClassification(
            intent="build",
            reasoning=f"Classification failed ({str(e)}), defaulting to build"
        )


def create_backend_builder_node(
    interactive: bool = True
) -> Callable[[ParentGraphState], Dict[str, Any]]:
    """
    Create a wrapper node that invokes the backend builder subgraph.
    
    This is a thin wrapper that delegates all logic to run_builder(),
    which handles clarification, continuation, checkpointing, etc.
    """
    def backend_builder_node(state: ParentGraphState) -> Dict[str, Any]:
        working = state["working"]
        
        requirements = working.get("initial_requirements", "")
        thread_id = working.get("builder_thread_id")
        
        if not requirements:
            return {
                "working": {
                    "error": "No requirements provided"
                }
            }
        
        try:
            result = run_builder(
                requirements=requirements,
                interactive=interactive,
                thread_id=thread_id,
                enable_checkpointing=True,
                checkpoint_type=CheckpointerType.SQLITE
            )
            
            return {
                "working": {
                    "backend_state": result
                }
            }
        except Exception as e:
            return {
                "working": {
                    "error": str(e)
                }
            }
    
    return backend_builder_node


def create_explainer_node(
    interactive: bool = True
) -> Callable[[ParentGraphState], Dict[str, Any]]:
    """
    Create a wrapper node that invokes the explainer subgraph.
    
    This handles user questions about the generated backend.
    """
    def explainer_node(state: ParentGraphState) -> Dict[str, Any]:
        working = state["working"]
        archive = state["archive"]
        
        user_question = working.get("initial_requirements", "")
        
        # Build context from existing backend results
        backend_context = {}
        
        if archive.get("final_ddl_script"):
            backend_context["ddl_script"] = archive["final_ddl_script"]
        
        if archive.get("final_erd_diagram"):
            backend_context["erd_diagram"] = archive["final_erd_diagram"]
        
        if archive.get("final_nestjs_architecture"):
            backend_context["nestjs_architecture"] = archive["final_nestjs_architecture"]
        
        # Include working state from backend if available
        backend_state = working.get("backend_state")
        if backend_state:
            backend_context["working"] = backend_state.get("working", {})
        
        try:
            explanation = run_explainer(
                user_question=user_question,
                backend_context=backend_context if backend_context else None,
                interactive=interactive
            )
            
            return {
                "working": {
                    "current_subgraph": "explainer_complete"
                },
                "archive": {
                    "workflow_history": [{
                        "step": "explainer",
                        "timestamp": datetime.utcnow().isoformat(),
                        "question": user_question,
                        "explanation": explanation[:500] + "..." if len(explanation) > 500 else explanation
                    }]
                }
            }
        except Exception as e:
            return {
                "working": {
                    "error": str(e)
                }
            }
    
    return explainer_node


# ============================================================
# PARENT GRAPH NODES
# ============================================================

def initialize_workflow(state: ParentGraphState) -> dict:
    """Initialize the parent workflow"""
    print(f"\n🚀 Initializing workflow...")
    
    return {
        "working": {
            "current_subgraph": "initializing"
        },
        "archive": {
            "workflow_history": [{
                "step": "initialize",
                "timestamp": datetime.utcnow().isoformat(),
                "mode": state['working']['mode'].value
            }]
        }
    }


def route_intent(state: ParentGraphState) -> dict:
    """
    Use LLM to classify user intent and determine which subgraph to call.
    """
    working = state["working"]
    archive = state["archive"]
    
    user_input = working.get("initial_requirements", "")
    has_backend = bool(archive.get("final_ddl_script") or archive.get("backend_results"))
    
    print("\n🔍 Analyzing user intent...")
    
    classification = classify_intent(user_input, has_backend)
    
    print(f"   Intent: {classification.intent}")
    print(f"   Reason: {classification.reasoning}")
    
    return {
        "working": {
            "current_subgraph": "intent_router",
            "user_intent": classification.intent,
            "intent_reasoning": classification.reasoning
        }
    }


def prepare_backend_builder(state: ParentGraphState) -> dict:
    """
    Prepare state for backend builder subgraph.
    Transform parent state into builder's expected format.
    """
    print("\n📦 Preparing Backend Builder subgraph...")
    
    working = state["working"]
    
    # Create execution tracking
    execution: SubgraphExecution = {
        "name": "backend_builder",
        "status": SubgraphStatus.IN_PROGRESS,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "llm_calls": 0,
        "error": None
    }
    
    # Transform parent state to builder state format
    builder_input = {
        "working": {
            "user_requirements": working["initial_requirements"],
            "sql_dialect": "postgresql",
            "enable_critic": True,
            "generate_nestjs": True,
            "current_step": "initialized",
            "current_task_id": None,
            "task_summary": [],
            "entities": [],
            "relationships": [],
            "tables": [],
            "critic_summary": None,
            "critic_revision_count": 0,
            "max_critic_revisions": 2,
            "validation_issues": [],
            "iteration_count": 0,
            "max_iterations": 10,
            "needs_clarification": False,
            "is_complete": False,
            "error": None,
            "thread_id": working.get("builder_thread_id")
        },
        "archive": {
            "tasks": [],
            "clarifying_questions": [],
            "user_answers": [],
            "critic_reports": [],
            "ddl_script": "",
            "erd_diagram": "",
            "nestjs_architecture": None,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "total_llm_calls": 0,
            "schema_versions": []
        }
    }
    
    return {
        "working": {
            "current_subgraph": "backend_builder",
            "backend_state": builder_input,
            "subgraph_executions": state["working"]["subgraph_executions"] + [execution]
        }
    }


def process_backend_results(state: ParentGraphState) -> dict:
    """
    Process results from backend builder subgraph.
    Extract and transform results into parent state.
    """
    print("\n✅ Processing Backend Builder results...")
    
    backend_state = state["working"].get("backend_state")
    if not backend_state:
        return {
            "working": {"error": "No backend state found"},
            "archive": {"backend_results": None}
        }
    
    # Extract results from backend builder
    archive = backend_state.get("archive", {})
    
    # Update execution tracking
    executions = state["working"]["subgraph_executions"].copy()
    for execution in reversed(executions):
        if execution["name"] == "backend_builder" and execution["status"] == SubgraphStatus.IN_PROGRESS:
            execution["status"] = SubgraphStatus.COMPLETED
            execution["completed_at"] = datetime.utcnow().isoformat()
            execution["llm_calls"] = archive.get("total_llm_calls", 0)
            break
    
    # Save version snapshot
    version = {
        "version": 1,
        "timestamp": datetime.utcnow().isoformat(),
        "ddl_script": archive.get("ddl_script"),
        "erd_diagram": archive.get("erd_diagram"),
        "nestjs_architecture": archive.get("nestjs_architecture"),
        "source": "backend_builder"
    }
    
    return {
        "working": {
            "current_subgraph": "backend_builder_complete",
            "subgraph_executions": executions
        },
        "archive": {
            "backend_results": archive,
            "final_ddl_script": archive.get("ddl_script"),
            "final_erd_diagram": archive.get("erd_diagram"),
            "final_nestjs_architecture": archive.get("nestjs_architecture"),
            "total_llm_calls": archive.get("total_llm_calls", 0),
            "versions": [version],
            "workflow_history": [{
                "step": "backend_builder_complete",
                "timestamp": datetime.utcnow().isoformat(),
                "llm_calls": archive.get("total_llm_calls", 0)
            }]
        }
    }


def finalize_workflow(state: ParentGraphState) -> dict:
    """Finalize the workflow and prepare final outputs"""
    print("\n🎉 Finalizing workflow...")
    
    return {
        "working": {
            "is_complete": True,
            "current_subgraph": "complete"
        },
        "archive": {
            "completed_at": datetime.utcnow().isoformat(),
            "workflow_history": [{
                "step": "finalize",
                "timestamp": datetime.utcnow().isoformat(),
                "total_versions": len(state["archive"]["versions"]),
                "total_enhancements": len(state["archive"]["enhancement_results"])
            }]
        }
    }


# ============================================================
# CONDITIONAL EDGES
# ============================================================

def route_by_intent(state: ParentGraphState) -> str:
    """Route to appropriate subgraph based on classified intent."""
    intent = state["working"].get("user_intent", "build")
    
    if intent == "explain":
        return "explain"
    else:
        return "build"


# ============================================================
# GRAPH CONSTRUCTION
# ============================================================

def build_parent_graph(
    checkpointer: Optional[BaseCheckpointSaver] = None,
    interactive: bool = True
) -> StateGraph:
    """
    Build the parent graph that orchestrates subgraphs.
    
    Uses LLM to route user requests to appropriate subgraph:
    - Backend Builder: For building/modifying backends
    - Explainer: For explaining the generated backend
    
    Args:
        checkpointer: Optional checkpointer for parent graph state persistence
        interactive: If True, subgraphs prompt user for input.
    
    Returns:
        Compiled parent StateGraph
    """
    workflow = StateGraph(ParentGraphState)
    
    # Add routing nodes
    workflow.add_node("initialize", initialize_workflow)
    workflow.add_node("route_intent", route_intent)
    
    # Add builder subgraph nodes
    workflow.add_node("prepare_builder", prepare_backend_builder)
    backend_builder_node = create_backend_builder_node(interactive=interactive)
    workflow.add_node("backend_builder", backend_builder_node)
    workflow.add_node("process_builder_results", process_backend_results)
    
    # Add explainer subgraph node
    explainer_node = create_explainer_node(interactive=interactive)
    workflow.add_node("explainer", explainer_node)
    
    # Add finalize node
    workflow.add_node("finalize", finalize_workflow)
    
    # Build workflow
    workflow.set_entry_point("initialize")
    workflow.add_edge("initialize", "route_intent")
    
    # Route based on intent
    workflow.add_conditional_edges(
        "route_intent",
        route_by_intent,
        {
            "build": "prepare_builder",
            "explain": "explainer"
        }
    )
    
    # Builder path
    workflow.add_edge("prepare_builder", "backend_builder")
    workflow.add_edge("backend_builder", "process_builder_results")
    workflow.add_edge("process_builder_results", "finalize")
    
    # Explainer path
    workflow.add_edge("explainer", "finalize")
    
    workflow.add_edge("finalize", END)
    
    # Compile with checkpointing
    return workflow.compile(checkpointer=checkpointer)