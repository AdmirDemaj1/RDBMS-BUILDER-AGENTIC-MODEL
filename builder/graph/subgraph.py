# graph/subgraph.py
"""
RDBMS Builder Subgraph Module

This module exposes the RDBMS builder as a subgraph that can be integrated
into a parent graph. When the parent graph determines the user wants to 
generate a backend, it can invoke this subgraph.

Usage in parent graph:
    from graph.subgraph import (
        get_rdbms_builder_subgraph,
        RDBMSBuilderInput,
        RDBMSBuilderOutput,
        create_rdbms_node
    )
    
    # Option 1: Use as a compiled subgraph (recommended)
    parent_graph.add_node("generate_backend", get_rdbms_builder_subgraph())
    
    # Option 2: Use as a wrapped node function  
    parent_graph.add_node("generate_backend", create_rdbms_node())
"""

from typing import TypedDict, Optional, Any, Dict, Callable, List
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.base import BaseCheckpointSaver

from .builder import build_graph, build_graph_continue
from .state import (
    GraphState,
    WorkingState,
    ArchiveState,
    Entity,
    Relationship,
    Table,
    NestJSArchitecture
)
from ..utils.state_manager import StateManager


# ============================================================
# INPUT/OUTPUT TYPES FOR PARENT GRAPH INTEGRATION
# ============================================================

class RDBMSBuilderInput(TypedDict):
    """
    Input schema for the RDBMS builder subgraph.
    Parent graph should populate these fields before invoking.
    """
    user_requirements: str
    sql_dialect: Optional[str]  # Default: "postgresql"
    enable_critic: Optional[bool]  # Default: True
    generate_nestjs: Optional[bool]  # Default: True
    thread_id: Optional[str]  # For checkpointing continuity


class RDBMSBuilderOutput(TypedDict):
    """
    Output schema from the RDBMS builder subgraph.
    Parent graph receives these fields after execution.
    """
    # Schema outputs
    ddl_script: str
    erd_diagram: str
    entities: List[Entity]
    relationships: List[Relationship]
    tables: List[Table]
    
    # NestJS outputs (if enabled)
    nestjs_architecture: Optional[NestJSArchitecture]
    
    # Execution metadata
    is_complete: bool
    needs_clarification: bool
    clarifying_questions: Optional[List[Dict[str, Any]]]
    error: Optional[str]
    total_llm_calls: int


# ============================================================
# SUBGRAPH FACTORY FUNCTIONS
# ============================================================

def get_rdbms_builder_subgraph(
    checkpointer: Optional[BaseCheckpointSaver] = None
) -> StateGraph:
    """
    Get the RDBMS builder as a compiled subgraph.
    
    This is the recommended way to use the RDBMS builder as a subgraph.
    The compiled graph can be added directly as a node to the parent graph.
    
    Args:
        checkpointer: Optional checkpointer for persistence
        
    Returns:
        Compiled StateGraph ready to be used as a subgraph
        
    Example:
        parent_workflow = StateGraph(ParentState)
        rdbms_subgraph = get_rdbms_builder_subgraph(checkpointer)
        parent_workflow.add_node("generate_backend", rdbms_subgraph)
    """
    return build_graph(checkpointer=checkpointer)


def get_rdbms_continue_subgraph(
    checkpointer: Optional[BaseCheckpointSaver] = None
) -> StateGraph:
    """
    Get the continuation subgraph for resuming after clarification.
    
    Args:
        checkpointer: Optional checkpointer for persistence
        
    Returns:
        Compiled StateGraph for continuation
    """
    return build_graph_continue(checkpointer=checkpointer)


# ============================================================
# NODE WRAPPER FUNCTIONS
# ============================================================

def create_rdbms_node(
    checkpointer: Optional[BaseCheckpointSaver] = None,
    auto_continue: bool = True
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    Create a node function that wraps the RDBMS builder.
    
    This provides more control over how the subgraph is invoked and
    how state is transformed between parent and subgraph.
    
    Args:
        checkpointer: Optional checkpointer for persistence
        auto_continue: If True, automatically continues after clarification
        
    Returns:
        A callable node function for the parent graph
        
    Example:
        parent_workflow = StateGraph(ParentState)
        rdbms_node = create_rdbms_node(checkpointer)
        parent_workflow.add_node("generate_backend", rdbms_node)
    """
    graph = build_graph(checkpointer=checkpointer)
    graph_continue = build_graph_continue(checkpointer=checkpointer)
    
    def rdbms_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Node function that executes the RDBMS builder.
        
        Expects parent state to have 'rdbms_input' field with RDBMSBuilderInput,
        or extracts from parent state fields directly.
        """
        # Extract input from parent state
        rdbms_input: RDBMSBuilderInput = state.get("rdbms_input", {})
        
        # Allow fallback to direct parent state fields
        user_requirements = rdbms_input.get("user_requirements") or state.get("user_requirements", "")
        sql_dialect = rdbms_input.get("sql_dialect") or state.get("sql_dialect", "postgresql")
        enable_critic = rdbms_input.get("enable_critic", True)
        generate_nestjs = rdbms_input.get("generate_nestjs", True)
        thread_id = rdbms_input.get("thread_id") or state.get("thread_id")
        
        # Create initial state for the subgraph
        subgraph_state = StateManager.create_initial_state(
            requirements=user_requirements,
            dialect=sql_dialect,
            enable_critic=enable_critic,
            generate_nestjs=generate_nestjs,
            thread_id=thread_id
        )
        
        # Create config for checkpointing
        config = {}
        if thread_id:
            config["configurable"] = {"thread_id": thread_id}
        
        # Execute the subgraph
        result = graph.invoke(subgraph_state, config=config)
        
        # Handle clarification with auto-continue
        if result["working"].get("needs_clarification") and auto_continue:
            result["working"]["needs_clarification"] = False
            result = graph_continue.invoke(result, config=config)
        
        # Transform result to output format
        output: RDBMSBuilderOutput = {
            "ddl_script": result["archive"].get("ddl_script", ""),
            "erd_diagram": result["archive"].get("erd_diagram", ""),
            "entities": result["working"].get("entities", []),
            "relationships": result["working"].get("relationships", []),
            "tables": result["working"].get("tables", []),
            "nestjs_architecture": result["archive"].get("nestjs_architecture"),
            "is_complete": result["working"].get("is_complete", False),
            "needs_clarification": result["working"].get("needs_clarification", False),
            "clarifying_questions": result["archive"].get("clarifying_questions"),
            "error": result["working"].get("error"),
            "total_llm_calls": result["archive"].get("total_llm_calls", 0)
        }
        
        # Return output to be merged into parent state
        return {"rdbms_output": output}
    
    return rdbms_node


def create_rdbms_node_with_state_mapping(
    checkpointer: Optional[BaseCheckpointSaver] = None,
    input_mapper: Optional[Callable[[Dict[str, Any]], RDBMSBuilderInput]] = None,
    output_mapper: Optional[Callable[[RDBMSBuilderOutput], Dict[str, Any]]] = None,
    auto_continue: bool = True
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    Create a node function with custom state mapping.
    
    This is useful when your parent graph has a different state structure
    and you need to transform between them.
    
    Args:
        checkpointer: Optional checkpointer for persistence
        input_mapper: Function to extract RDBMSBuilderInput from parent state
        output_mapper: Function to transform output to parent state format
        auto_continue: If True, automatically continues after clarification
        
    Returns:
        A callable node function for the parent graph
        
    Example:
        def my_input_mapper(parent_state):
            return RDBMSBuilderInput(
                user_requirements=parent_state["project_description"],
                sql_dialect="postgresql"
            )
        
        def my_output_mapper(rdbms_output):
            return {"generated_sql": rdbms_output["ddl_script"]}
        
        node = create_rdbms_node_with_state_mapping(
            input_mapper=my_input_mapper,
            output_mapper=my_output_mapper
        )
    """
    graph = build_graph(checkpointer=checkpointer)
    graph_continue = build_graph_continue(checkpointer=checkpointer)
    
    def default_input_mapper(state: Dict[str, Any]) -> RDBMSBuilderInput:
        return RDBMSBuilderInput(
            user_requirements=state.get("user_requirements", ""),
            sql_dialect=state.get("sql_dialect", "postgresql"),
            enable_critic=state.get("enable_critic", True),
            generate_nestjs=state.get("generate_nestjs", True),
            thread_id=state.get("thread_id")
        )
    
    def default_output_mapper(output: RDBMSBuilderOutput) -> Dict[str, Any]:
        return {"rdbms_output": output}
    
    actual_input_mapper = input_mapper or default_input_mapper
    actual_output_mapper = output_mapper or default_output_mapper
    
    def rdbms_node(state: Dict[str, Any]) -> Dict[str, Any]:
        # Map input
        rdbms_input = actual_input_mapper(state)
        
        # Create initial state
        subgraph_state = StateManager.create_initial_state(
            requirements=rdbms_input.get("user_requirements", ""),
            dialect=rdbms_input.get("sql_dialect", "postgresql"),
            enable_critic=rdbms_input.get("enable_critic", True),
            generate_nestjs=rdbms_input.get("generate_nestjs", True),
            thread_id=rdbms_input.get("thread_id")
        )
        
        config = {}
        if rdbms_input.get("thread_id"):
            config["configurable"] = {"thread_id": rdbms_input["thread_id"]}
        
        # Execute
        result = graph.invoke(subgraph_state, config=config)
        
        # Handle clarification
        if result["working"].get("needs_clarification") and auto_continue:
            result["working"]["needs_clarification"] = False
            result = graph_continue.invoke(result, config=config)
        
        # Create output
        output: RDBMSBuilderOutput = {
            "ddl_script": result["archive"].get("ddl_script", ""),
            "erd_diagram": result["archive"].get("erd_diagram", ""),
            "entities": result["working"].get("entities", []),
            "relationships": result["working"].get("relationships", []),
            "tables": result["working"].get("tables", []),
            "nestjs_architecture": result["archive"].get("nestjs_architecture"),
            "is_complete": result["working"].get("is_complete", False),
            "needs_clarification": result["working"].get("needs_clarification", False),
            "clarifying_questions": result["archive"].get("clarifying_questions"),
            "error": result["working"].get("error"),
            "total_llm_calls": result["archive"].get("total_llm_calls", 0)
        }
        
        # Map output
        return actual_output_mapper(output)
    
    return rdbms_node


# ============================================================
# DIRECT INVOCATION HELPER
# ============================================================

def invoke_rdbms_builder(
    requirements: str,
    dialect: str = "postgresql",
    enable_critic: bool = True,
    generate_nestjs: bool = True,
    thread_id: Optional[str] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None
) -> RDBMSBuilderOutput:
    """
    Directly invoke the RDBMS builder without integrating into a graph.
    
    This is a convenience function for when you want to call the builder
    programmatically without setting up a parent graph.
    
    Args:
        requirements: User requirements for the database schema
        dialect: SQL dialect (postgresql, mysql, sqlite)
        enable_critic: Whether to enable schema critique
        generate_nestjs: Whether to generate NestJS architecture
        thread_id: Optional thread ID for checkpointing
        checkpointer: Optional checkpointer for persistence
        
    Returns:
        RDBMSBuilderOutput with all generated artifacts
        
    Example:
        result = invoke_rdbms_builder(
            requirements="Build an e-commerce system with products and orders",
            dialect="postgresql",
            generate_nestjs=True
        )
        print(result["ddl_script"])
    """
    node_fn = create_rdbms_node(checkpointer=checkpointer, auto_continue=True)
    
    state = {
        "rdbms_input": RDBMSBuilderInput(
            user_requirements=requirements,
            sql_dialect=dialect,
            enable_critic=enable_critic,
            generate_nestjs=generate_nestjs,
            thread_id=thread_id
        )
    }
    
    result = node_fn(state)
    return result["rdbms_output"]


# ============================================================
# FULL STATE SUBGRAPH (Alternative approach)
# ============================================================

def get_full_state_subgraph(
    checkpointer: Optional[BaseCheckpointSaver] = None
) -> StateGraph:
    """
    Get the RDBMS builder that uses the full GraphState.
    
    Use this when your parent graph uses the same GraphState structure,
    or when you want to embed the subgraph directly without state transformation.
    
    The parent graph should use GraphState or a compatible state type.
    
    Args:
        checkpointer: Optional checkpointer for persistence
        
    Returns:
        Compiled StateGraph using full GraphState
    """
    return build_graph(checkpointer=checkpointer)

