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


def build_graph() -> StateGraph:
    workflow = StateGraph(GraphState)
    
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
    
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "clarify")
    
    workflow.add_conditional_edges("clarify", should_clarify, {
        "needs_clarification": END,
        "proceed": "extract_entities"
    })
    
    workflow.add_edge("extract_entities", "analyze_relationships")
    workflow.add_edge("analyze_relationships", "design_schema")
    workflow.add_edge("design_schema", "validate_schema")
    
    workflow.add_conditional_edges("validate_schema", should_run_critic, {
        "run_critic": "critic",
        "generate_outputs": "generate_sql"
    })
    
    workflow.add_conditional_edges("critic", should_refine, {
        "refine": "refine_schema",
        "generate_outputs": "generate_sql"
    })
    
    workflow.add_conditional_edges("refine_schema", should_re_critique, {
        "re_critique": "critic",
        "generate_outputs": "generate_sql"
    })
    
    workflow.add_edge("generate_sql", "generate_erd")
    workflow.add_edge("generate_erd", END)
    
    return workflow.compile()


def build_graph_continue() -> StateGraph:
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
    
    workflow.add_conditional_edges("validate_schema", should_run_critic, {
        "run_critic": "critic",
        "generate_outputs": "generate_sql"
    })
    
    workflow.add_conditional_edges("critic", should_refine, {
        "refine": "refine_schema",
        "generate_outputs": "generate_sql"
    })
    
    workflow.add_conditional_edges("refine_schema", should_re_critique, {
        "re_critique": "critic",
        "generate_outputs": "generate_sql"
    })
    
    workflow.add_edge("generate_sql", "generate_erd")
    workflow.add_edge("generate_erd", END)
    
    return workflow.compile()


graph = build_graph()
graph_continue = build_graph_continue()