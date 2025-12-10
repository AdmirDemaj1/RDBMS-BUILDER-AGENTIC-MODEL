# graph/nodes/planner.py
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import GraphState, Task, TaskStatus
from utils.llm import get_llm
from utils.task_manager import create_task, get_default_tasks, print_task_summary
from pydantic import BaseModel, Field


class TaskItem(BaseModel):
    """A single task in the plan."""
    content: str = Field(description="Description of what this task will accomplish")
    node_name: str = Field(description="The node that will execute this task")


class ExecutionPlan(BaseModel):
    """The complete execution plan."""
    tasks: List[TaskItem] = Field(description="Ordered list of tasks to execute")
    reasoning: str = Field(description="Brief explanation of the plan")


PLANNER_PROMPT = """You are a database architect creating an execution plan for building a database schema.

Given the software requirements, create a task list. Each task must map to one of these nodes:
- clarify: Analyze requirements and identify any ambiguities
- extract_entities: Identify all entities/objects from the requirements
- analyze_relationships: Determine how entities relate to each other
- design_schema: Create table structures with columns, types, and constraints
- validate_schema: Check for normalization, missing foreign keys, etc.
- critic: Critically evaluate the schema design quality
- refine_schema: Improve schema based on critic feedback
- generate_sql: Generate the SQL DDL script
- generate_erd: Create an ERD diagram in Mermaid format

IMPORTANT:
- Include ALL nodes in the plan in the correct order
- The critic and refine_schema nodes help improve quality
- Make task descriptions specific to the given requirements
- Each node should appear exactly once
"""


def planner(state: GraphState) -> Dict[str, Any]:
    """
    Node that creates an execution plan with specific tasks.
    """
    print("\n" + "=" * 60)
    print("📋 CREATING EXECUTION PLAN")
    print("=" * 60)
    print(f"Analyzing requirements to create task plan...\n")
    
    enable_critic = state.get('enable_critic', True)
    
    llm = get_llm()
    
    try:
        structured_llm = llm.with_structured_output(ExecutionPlan)
        
        messages = [
            SystemMessage(content=PLANNER_PROMPT),
            HumanMessage(content=f"""Create an execution plan for these requirements:

{state['user_requirements']}

Create specific tasks that reference the actual entities and features mentioned.
{"Include critic and refine_schema tasks for quality improvement." if enable_critic else "Skip critic and refine_schema tasks."}""")
        ]
        
        result = structured_llm.invoke(messages)
        
        # Validate required nodes
        required_nodes = {"clarify", "extract_entities", "analyze_relationships", 
                        "design_schema", "validate_schema", "generate_sql", "generate_erd"}
        
        if enable_critic:
            required_nodes.update({"critic", "refine_schema"})
        
        plan_nodes = {task.node_name for task in result.tasks}
        
        if required_nodes.issubset(plan_nodes):
            tasks = [
                create_task(task.content, task.node_name)
                for task in result.tasks
            ]
            print(f"✅ Created customized plan with {len(tasks)} tasks")
            print(f"   Reasoning: {result.reasoning}\n")
        else:
            missing = required_nodes - plan_nodes
            print(f"⚠️ Plan missing nodes: {missing}, using default plan")
            tasks = get_default_tasks(enable_critic=enable_critic)
            
    except Exception as e:
        print(f"⚠️ Could not create custom plan: {e}")
        print("   Using default task plan...")
        tasks = get_default_tasks(enable_critic=enable_critic)
    
    print_task_summary(tasks)
    
    return {
        "tasks": tasks,
        "current_task_id": None,
        "current_step": "planning_complete"
    }