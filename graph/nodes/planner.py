# graph/nodes/planner.py
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import GraphState
from utils.llm import get_llm
from utils.state_manager import StateManager
from utils.task_manager import create_task, get_default_tasks, print_task_summary
from pydantic import BaseModel, Field


class TaskItem(BaseModel):
    content: str
    node_name: str


class ExecutionPlan(BaseModel):
    tasks: List[TaskItem]
    reasoning: str


PLANNER_PROMPT = """Create an execution plan for database schema generation.

Nodes (in order): clarify, extract_entities, analyze_relationships, design_schema, validate_schema, critic, refine_schema, generate_sql, generate_erd, generate_nestjs

For each node, create ONE specific task that:
- References entities/relationships from requirements
- Anticipates domain-specific challenges
- Provides actionable direction

Include ALL nodes. Tailor to the domain (e-commerce, healthcare, etc.)."""


def planner(state: GraphState) -> GraphState:
    print("\n" + "=" * 60)
    print("📋 CREATING EXECUTION PLAN")
    print("=" * 60)
    
    working = state["working"]
    enable_critic = working.get("enable_critic", True)
    generate_nestjs = working.get("generate_nestjs", True)
    requirements = working["user_requirements"]
    
    llm = get_llm()
    
    try:
        structured_llm = llm.with_structured_output(ExecutionPlan)
        
        messages = [
            SystemMessage(content=PLANNER_PROMPT),
            HumanMessage(content=f"Requirements:\n{requirements[:1000]}")
        ]
        
        result = structured_llm.invoke(messages)
        StateManager.increment_llm_calls(state)
        
        required_nodes = {"clarify", "extract_entities", "analyze_relationships",
                         "design_schema", "validate_schema", "generate_sql", "generate_erd"}
        if enable_critic:
            required_nodes.update({"critic", "refine_schema"})
        if generate_nestjs:
            required_nodes.add("generate_nestjs")
        
        plan_nodes = {t.node_name for t in result.tasks}
        
        if required_nodes.issubset(plan_nodes):
            # Filter out generate_nestjs if not enabled
            filtered_tasks = result.tasks
            if not generate_nestjs:
                filtered_tasks = [t for t in result.tasks if t.node_name != "generate_nestjs"]
            tasks = [create_task(t.content, t.node_name) for t in filtered_tasks]
            print(f"✅ Created plan with {len(tasks)} tasks")
        else:
            tasks = get_default_tasks(enable_critic, generate_nestjs)
            print("⚠️ Using default plan")
            
    except Exception as e:
        print(f"⚠️ Plan error: {e}, using default")
        tasks = get_default_tasks(enable_critic, generate_nestjs)
    
    for task in tasks:
        StateManager.add_task(state, task)
    
    state["working"]["current_step"] = "planning_complete"
    
    print_task_summary(state)
    
    return state