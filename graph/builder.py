# graph/builder.py
from langgraph.graph import StateGraph, END, START
from graph.state import GraphState
from graph.nodes import (
    planner,
    clarifier,
    entity_extractor,
    relationship_analyzer,
    schema_designer,
    validator,
    verify_initial_schema,
    critic,
    schema_refiner,
    verify_refinements,
    sql_generator,
    erd_generator,
    nestjs_generator
)


def should_clarify(state: GraphState) -> str:
    if state["working"].get("needs_clarification", False):
        return "needs_clarification"
    return "proceed"


def should_run_critic(state: GraphState) -> str:
    if state["working"].get("enable_critic", True):
        return "run_critic"
    return "generate_outputs"


def should_refine(state: GraphState) -> str:
    working = state["working"]
    summary = working.get("critic_summary")
    revision_count = working.get("critic_revision_count", 0)
    max_revisions = working.get("max_critic_revisions", 2)
    
    if not summary:
        return "generate_outputs"
    
    if summary.get("requires_revision") and revision_count <= max_revisions:
        return "refine"
    
    return "generate_outputs"


def should_re_critique(state: GraphState) -> str:
    working = state["working"]
    revision_count = working.get("critic_revision_count", 0)
    max_revisions = working.get("max_critic_revisions", 2)
    
    if revision_count < max_revisions:
        return "re_critique"
    return "generate_outputs"


def aggregator(state: GraphState) -> dict:
    """
    Aggregator node that waits for all parallel generation tasks to complete.
    This node doesn't modify state, it just acts as a synchronization point.
    """
    return {}


def parallel_trigger(state: GraphState) -> dict:
    """
    Trigger node for parallel execution.
    This node acts as the branching point for parallel generation tasks.
    """
    return {}


def build_graph() -> StateGraph:
    workflow = StateGraph(GraphState)
    
    # Add all nodes
    workflow.add_node("plan", planner)
    workflow.add_node("clarify", clarifier)
    workflow.add_node("extract_entities", entity_extractor)
    workflow.add_node("analyze_relationships", relationship_analyzer)
    workflow.add_node("design_schema", schema_designer)
    workflow.add_node("verify_initial_schema", verify_initial_schema)  # NEW: Validate initial design
    workflow.add_node("validate_schema", validator)
    workflow.add_node("critic", critic)
    workflow.add_node("refine_schema", schema_refiner)
    workflow.add_node("verify_refinements", verify_refinements)  # NEW: Validate refinements
    workflow.add_node("parallel_trigger", parallel_trigger)  # New trigger node
    workflow.add_node("generate_sql", sql_generator)
    workflow.add_node("generate_erd", erd_generator)
    workflow.add_node("generate_nestjs", nestjs_generator)
    workflow.add_node("aggregator", aggregator)
    
    # Set entry point
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "clarify")
    
    # Clarification conditional
    workflow.add_conditional_edges("clarify", should_clarify, {
        "needs_clarification": END,
        "proceed": "extract_entities"
    })
    
    # Sequential processing up to validation
    workflow.add_edge("extract_entities", "analyze_relationships")
    workflow.add_edge("analyze_relationships", "design_schema")
    workflow.add_edge("design_schema", "verify_initial_schema")  # NEW: Verify initial design
    workflow.add_edge("verify_initial_schema", "validate_schema")
    
    # Critic workflow - all paths lead to parallel_trigger
    workflow.add_conditional_edges("validate_schema", should_run_critic, {
        "run_critic": "critic",
        "generate_outputs": "parallel_trigger"  # Go to trigger node
    })
    
    workflow.add_conditional_edges("critic", should_refine, {
        "refine": "refine_schema",
        "generate_outputs": "parallel_trigger"  # Go to trigger node
    })
    
    # NEW: Verify refinements before sending back to critic
    workflow.add_edge("refine_schema", "verify_refinements")
    
    workflow.add_conditional_edges("verify_refinements", should_re_critique, {
        "re_critique": "critic",
        "generate_outputs": "parallel_trigger"  # Go to trigger node
    })
    
    # PARALLEL EXECUTION: Branch from parallel_trigger to all three generators
    workflow.add_edge("parallel_trigger", "generate_sql")
    workflow.add_edge("parallel_trigger", "generate_erd")
    workflow.add_edge("parallel_trigger", "generate_nestjs")
    
    # All three generators converge at aggregator
    workflow.add_edge("generate_sql", "aggregator")
    workflow.add_edge("generate_erd", "aggregator")
    workflow.add_edge("generate_nestjs", "aggregator")
    
    # Aggregator completes the workflow
    workflow.add_edge("aggregator", END)
    
    return workflow.compile()


def build_graph_continue() -> StateGraph:
    """
    Continuation graph for resuming after clarification.
    Also uses parallel execution for generators.
    """
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("extract_entities", entity_extractor)
    workflow.add_node("analyze_relationships", relationship_analyzer)
    workflow.add_node("design_schema", schema_designer)
    workflow.add_node("verify_initial_schema", verify_initial_schema)  # NEW
    workflow.add_node("validate_schema", validator)
    workflow.add_node("critic", critic)
    workflow.add_node("refine_schema", schema_refiner)
    workflow.add_node("verify_refinements", verify_refinements)  # NEW
    workflow.add_node("parallel_trigger", parallel_trigger)
    workflow.add_node("generate_sql", sql_generator)
    workflow.add_node("generate_erd", erd_generator)
    workflow.add_node("generate_nestjs", nestjs_generator)
    workflow.add_node("aggregator", aggregator)
    
    # Set entry point
    workflow.set_entry_point("extract_entities")
    
    # Sequential processing
    workflow.add_edge("extract_entities", "analyze_relationships")
    workflow.add_edge("analyze_relationships", "design_schema")
    workflow.add_edge("design_schema", "verify_initial_schema")  # NEW
    workflow.add_edge("verify_initial_schema", "validate_schema")
    
    # Critic workflow
    workflow.add_conditional_edges("validate_schema", should_run_critic, {
        "run_critic": "critic",
        "generate_outputs": "parallel_trigger"
    })
    
    workflow.add_conditional_edges("critic", should_refine, {
        "refine": "refine_schema",
        "generate_outputs": "parallel_trigger"
    })
    
    # NEW: Verify refinements before re-critiquing
    workflow.add_edge("refine_schema", "verify_refinements")
    
    workflow.add_conditional_edges("verify_refinements", should_re_critique, {
        "re_critique": "critic",
        "generate_outputs": "parallel_trigger"
    })
    
    # PARALLEL EXECUTION from trigger node
    workflow.add_edge("parallel_trigger", "generate_sql")
    workflow.add_edge("parallel_trigger", "generate_erd")
    workflow.add_edge("parallel_trigger", "generate_nestjs")
    
    # Converge at aggregator
    workflow.add_edge("generate_sql", "aggregator")
    workflow.add_edge("generate_erd", "aggregator")
    workflow.add_edge("generate_nestjs", "aggregator")
    
    workflow.add_edge("aggregator", END)
    
    return workflow.compile()


# Compile the graphs
graph = build_graph()
graph_continue = build_graph_continue()
