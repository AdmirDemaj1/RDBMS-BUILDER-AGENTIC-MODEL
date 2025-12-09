# graph/builder.py
from langgraph.graph import StateGraph, END
from graph.state import GraphState
from graph.nodes import (
    entity_extractor,
    relationship_analyzer,
    schema_designer,
    validator,
    sql_generator,
    clarifier,
    erd_generator
)


def should_clarify(state: GraphState) -> str:
    """
    Conditional edge: check if clarification is needed.
    """
    if state.get('needs_clarification', False):
        return "needs_clarification"
    return "proceed"


def should_continue_after_validation(state: GraphState) -> str:
    """
    Conditional edge: decide whether to refine schema or generate outputs.
    """
    issues = state.get('validation_issues', [])
    iterations = state.get('iteration_count', 0)
    max_iterations = state.get('max_iterations', 3)
    
    if not issues:
        return "generate_outputs"
    elif iterations >= max_iterations:
        print(f"⚠️  Max iterations ({max_iterations}) reached, proceeding with current schema")
        return "generate_outputs"
    else:
        return "refine_schema"


def build_graph() -> StateGraph:
    """
    Builds and returns the compiled RDBMS builder graph.
    """
    workflow = StateGraph(GraphState)
    
    # Add all nodes
    workflow.add_node("clarify", clarifier)
    workflow.add_node("extract_entities", entity_extractor)
    workflow.add_node("analyze_relationships", relationship_analyzer)
    workflow.add_node("design_schema", schema_designer)
    workflow.add_node("validate_schema", validator)
    workflow.add_node("generate_sql", sql_generator)
    workflow.add_node("generate_erd", erd_generator)
    
    # Define the flow
    # Start -> Clarify
    workflow.set_entry_point("clarify")
    
    # Clarify -> Conditional: Wait for answers or proceed
    workflow.add_conditional_edges(
        "clarify",
        should_clarify,
        {
            "needs_clarification": END,  # Stop and wait for user input
            "proceed": "extract_entities"
        }
    )
    
    # Extract Entities -> Analyze Relationships
    workflow.add_edge("extract_entities", "analyze_relationships")
    
    # Analyze Relationships -> Design Schema
    workflow.add_edge("analyze_relationships", "design_schema")
    
    # Design Schema -> Validate
    workflow.add_edge("design_schema", "validate_schema")
    
    # Validate -> Conditional: Generate outputs or Refine
    workflow.add_conditional_edges(
        "validate_schema",
        should_continue_after_validation,
        {
            "generate_outputs": "generate_sql",
            "refine_schema": "design_schema"
        }
    )
    
    # Generate SQL -> Generate ERD
    workflow.add_edge("generate_sql", "generate_erd")
    
    # Generate ERD -> End
    workflow.add_edge("generate_erd", END)
    
    return workflow.compile()


def build_graph_after_clarification() -> StateGraph:
    """
    Builds a graph that skips clarification (used after user provides answers).
    """
    workflow = StateGraph(GraphState)
    
    workflow.add_node("extract_entities", entity_extractor)
    workflow.add_node("analyze_relationships", relationship_analyzer)
    workflow.add_node("design_schema", schema_designer)
    workflow.add_node("validate_schema", validator)
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
            "generate_outputs": "generate_sql",
            "refine_schema": "design_schema"
        }
    )
    
    workflow.add_edge("generate_sql", "generate_erd")
    workflow.add_edge("generate_erd", END)
    
    return workflow.compile()


# Create singleton instances
graph = build_graph()
graph_after_clarification = build_graph_after_clarification()