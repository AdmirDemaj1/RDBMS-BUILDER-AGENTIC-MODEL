# graph/builder.py
from langgraph.graph import StateGraph, END
from graph.state import GraphState
from graph.nodes import (
    planner,
    clarifier,
    entity_extractor,
    relationship_analyzer,
    schema_designer,
    validator,
    critic,
    schema_refiner,
    sql_generator,
    erd_generator
)


def should_clarify(state: GraphState) -> str:
    """Check if clarification is needed."""
    if state.get('needs_clarification', False):
        return "needs_clarification"
    return "proceed"


def should_continue_after_validation(state: GraphState) -> str:
    """Decide whether to go to critic or generate outputs."""
    if state.get('enable_critic', True):
        return "run_critic"
    return "generate_outputs"


def should_refine_after_critic(state: GraphState) -> str:
    """Decide whether to refine based on critic feedback."""
    critic_reports = state.get('critic_reports', [])
    revision_count = state.get('critic_revision_count', 0)
    max_revisions = state.get('max_critic_revisions', 2)
    
    if not critic_reports:
        return "generate_outputs"
    
    latest_report = critic_reports[-1]
    
    # Check if revision is needed and we haven't exceeded max revisions
    if latest_report.get('requires_revision') and revision_count < max_revisions:
        return "refine"
    
    if revision_count >= max_revisions:
        print(f"⚠️ Max critic revisions ({max_revisions}) reached, proceeding with current schema")
    
    return "generate_outputs"


def should_revalidate_after_refine(state: GraphState) -> str:
    """After refinement, always re-run critic to verify improvements."""
    revision_count = state.get('critic_revision_count', 0)
    max_revisions = state.get('max_critic_revisions', 2)
    
    if revision_count < max_revisions:
        return "re_critique"
    
    return "generate_outputs"


def build_graph() -> StateGraph:
    """
    Builds the complete RDBMS builder graph with critic.
    
    Flow:
    1. Planner creates task list
    2. Clarifier checks for ambiguities
    3. If clarification needed -> END (wait for user)
    4. Entity extraction
    5. Relationship analysis  
    6. Schema design
    7. Validation
    8. Critic evaluation
    9. If revision needed -> Schema refinement -> Back to Critic
    10. SQL generation
    11. ERD generation
    """
    workflow = StateGraph(GraphState)
    
    # Add all nodes
    workflow.add_node("plan", planner)
    workflow.add_node("clarify", clarifier)
    workflow.add_node("extract_entities", entity_extractor)
    workflow.add_node("analyze_relationships", relationship_analyzer)
    workflow.add_node("design_schema", schema_designer)
    workflow.add_node("validate_schema", validator)
    workflow.add_node("critic", critic)
    workflow.add_node("refine_schema", schema_refiner)
    workflow.add_node("generate_sql", sql_generator)
    workflow.add_node("generate_erd", erd_generator)
    
    # Define the flow
    workflow.set_entry_point("plan")
    
    # Plan -> Clarify
    workflow.add_edge("plan", "clarify")
    
    # Clarify -> Conditional
    workflow.add_conditional_edges(
        "clarify",
        should_clarify,
        {
            "needs_clarification": END,
            "proceed": "extract_entities"
        }
    )
    
    # Main extraction flow
    workflow.add_edge("extract_entities", "analyze_relationships")
    workflow.add_edge("analyze_relationships", "design_schema")
    workflow.add_edge("design_schema", "validate_schema")
    
    # Validation -> Critic (if enabled) or generate outputs
    workflow.add_conditional_edges(
        "validate_schema",
        should_continue_after_validation,
        {
            "run_critic": "critic",
            "generate_outputs": "generate_sql"
        }
    )
    
    # Critic -> Conditional: Refine or Generate
    workflow.add_conditional_edges(
        "critic",
        should_refine_after_critic,
        {
            "refine": "refine_schema",
            "generate_outputs": "generate_sql"
        }
    )
    
    # Refine -> Conditional: Re-critique or Generate
    workflow.add_conditional_edges(
        "refine_schema",
        should_revalidate_after_refine,
        {
            "re_critique": "critic",
            "generate_outputs": "generate_sql"
        }
    )
    
    # Output generation
    workflow.add_edge("generate_sql", "generate_erd")
    workflow.add_edge("generate_erd", END)
    
    return workflow.compile()


def build_graph_continue() -> StateGraph:
    """
    Builds a graph that continues after clarification.
    """
    workflow = StateGraph(GraphState)
    
    workflow.add_node("extract_entities", entity_extractor)
    workflow.add_node("analyze_relationships", relationship_analyzer)
    workflow.add_node("design_schema", schema_designer)
    workflow.add_node("validate_schema", validator)
    workflow.add_node("critic", critic)
    workflow.add_node("refine_schema", schema_refiner)
    workflow.add_node("generate_sql", sql_generator)
    workflow.add_node("generate_erd", erd_generator)
    
    workflow.set_entry_point("extract_entities")
    
    workflow.add_edge("extract_entities", "analyze_relationships")
    workflow.add_edge("analyze_relationships", "design_schema")
    workflow.add_edge("design_schema", "validate_schema")
    
    workflow.add_conditional_edges(
        "validate_schema",
        should_continue_after_validation,
        {
            "run_critic": "critic",
            "generate_outputs": "generate_sql"
        }
    )
    
    workflow.add_conditional_edges(
        "critic",
        should_refine_after_critic,
        {
            "refine": "refine_schema",
            "generate_outputs": "generate_sql"
        }
    )
    
    workflow.add_conditional_edges(
        "refine_schema",
        should_revalidate_after_refine,
        {
            "re_critique": "critic",
            "generate_outputs": "generate_sql"
        }
    )
    
    workflow.add_edge("generate_sql", "generate_erd")
    workflow.add_edge("generate_erd", END)
    
    return workflow.compile()


# Create singleton instances
graph = build_graph()
graph_continue = build_graph_continue()