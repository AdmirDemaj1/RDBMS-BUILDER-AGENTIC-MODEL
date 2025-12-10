# utils/task_manager.py
from typing import Dict, Any, List, Optional
from graph.state import GraphState, Task, TaskStatus
import uuid


def create_task(content: str, node_name: str) -> Task:
    """Create a new task with a unique ID."""
    return {
        "id": str(uuid.uuid4())[:8],
        "content": content,
        "status": TaskStatus.PENDING,
        "node_name": node_name,
        "result": None,
        "error": None
    }


def get_task_by_id(tasks: List[Task], task_id: str) -> Optional[Task]:
    """Find a task by its ID."""
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None


def get_task_by_node(tasks: List[Task], node_name: str) -> Optional[Task]:
    """Find a task by its node name."""
    for task in tasks:
        if task["node_name"] == node_name:
            return task
    return None


def update_task(
    tasks: List[Task],
    task_id: str,
    status: Optional[TaskStatus] = None,
    result: Optional[str] = None,
    error: Optional[str] = None
) -> List[Task]:
    """Update a task's status, result, or error."""
    updated_tasks = []
    
    for task in tasks:
        if task["id"] == task_id:
            updated_task = task.copy()
            if status is not None:
                updated_task["status"] = status
            if result is not None:
                updated_task["result"] = result
            if error is not None:
                updated_task["error"] = error
            updated_tasks.append(updated_task)
        else:
            updated_tasks.append(task)
    
    return updated_tasks


def start_task(state: GraphState, node_name: str) -> Dict[str, Any]:
    """Mark a task as in progress when its node starts executing."""
    tasks = state.get("tasks", [])
    task = get_task_by_node(tasks, node_name)
    
    if task:
        print(f"\n{'='*60}")
        print(f"🔄 TASK IN PROGRESS: {task['content']}")
        print(f"{'='*60}")
        
        updated_tasks = update_task(tasks, task["id"], status=TaskStatus.IN_PROGRESS)
        return {
            "tasks": updated_tasks,
            "current_task_id": task["id"]
        }
    
    return {}


def complete_task(state: GraphState, node_name: str, result: str) -> Dict[str, Any]:
    """Mark a task as completed when its node finishes successfully."""
    tasks = state.get("tasks", [])
    task = get_task_by_node(tasks, node_name)
    
    if task:
        updated_tasks = update_task(
            tasks, 
            task["id"], 
            status=TaskStatus.COMPLETED,
            result=result
        )
        
        completed = sum(1 for t in updated_tasks if t["status"] == TaskStatus.COMPLETED)
        total = len(updated_tasks)
        percentage = (completed / total) * 100 if total > 0 else 0
        
        print(f"✅ TASK COMPLETED: {task['content']}")
        print(f"   Result: {result}")
        print(f"📊 Progress: {completed}/{total} ({percentage:.0f}%)")
        print_progress_bar(completed, total)
        
        return {
            "tasks": updated_tasks,
            "current_task_id": None
        }
    
    return {}


def fail_task(state: GraphState, node_name: str, error: str) -> Dict[str, Any]:
    """Mark a task as failed when its node encounters an error."""
    tasks = state.get("tasks", [])
    task = get_task_by_node(tasks, node_name)
    
    if task:
        updated_tasks = update_task(
            tasks,
            task["id"],
            status=TaskStatus.FAILED,
            error=error
        )
        
        print(f"❌ TASK FAILED: {task['content']}")
        print(f"   Error: {error}")
        
        return {
            "tasks": updated_tasks,
            "current_task_id": None,
            "error": error
        }
    
    return {"error": error}


def skip_task(state: GraphState, node_name: str, reason: str) -> Dict[str, Any]:
    """Mark a task as skipped."""
    tasks = state.get("tasks", [])
    task = get_task_by_node(tasks, node_name)
    
    if task:
        updated_tasks = update_task(
            tasks,
            task["id"],
            status=TaskStatus.SKIPPED,
            result=f"Skipped: {reason}"
        )
        
        print(f"⏭️ TASK SKIPPED: {task['content']}")
        print(f"   Reason: {reason}")
        
        return {
            "tasks": updated_tasks,
            "current_task_id": None
        }
    
    return {}


def print_progress_bar(completed: int, total: int, width: int = 40) -> None:
    """Print a visual progress bar."""
    if total == 0:
        return
        
    filled = int(width * completed / total)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    print(f"   [{bar}]")


def print_task_summary(tasks: List[Task]) -> None:
    """Print a summary of all tasks and their statuses."""
    print("\n" + "=" * 60)
    print("📋 TASK SUMMARY")
    print("=" * 60)
    
    status_icons = {
        TaskStatus.PENDING: "⏳",
        TaskStatus.IN_PROGRESS: "🔄",
        TaskStatus.COMPLETED: "✅",
        TaskStatus.FAILED: "❌",
        TaskStatus.SKIPPED: "⏭️"
    }
    
    for i, task in enumerate(tasks, 1):
        icon = status_icons.get(task["status"], "❓")
        print(f"{i}. {icon} {task['content']}")
        
        if task["result"]:
            print(f"      └─ Result: {task['result']}")
        if task["error"]:
            print(f"      └─ Error: {task['error']}")
    
    completed = sum(1 for t in tasks if t["status"] == TaskStatus.COMPLETED)
    failed = sum(1 for t in tasks if t["status"] == TaskStatus.FAILED)
    skipped = sum(1 for t in tasks if t["status"] == TaskStatus.SKIPPED)
    pending = sum(1 for t in tasks if t["status"] == TaskStatus.PENDING)
    
    print("-" * 60)
    print(f"Total: {len(tasks)} | ✅ {completed} | ❌ {failed} | ⏭️ {skipped} | ⏳ {pending}")
    print("=" * 60)


def get_default_tasks(enable_critic: bool = True) -> List[Task]:
    """
    Return the default task list for RDBMS schema generation.
    """
    task_definitions = [
        ("Analyze requirements and check for clarifications", "clarify"),
        ("Extract entities from requirements", "extract_entities"),
        ("Analyze relationships between entities", "analyze_relationships"),
        ("Design database schema with tables and columns", "design_schema"),
        ("Validate schema for normalization and constraints", "validate_schema"),
    ]
    
    # Add critic tasks if enabled
    if enable_critic:
        task_definitions.extend([
            ("Critic evaluation of schema design", "critic"),
            ("Refine schema based on critic feedback", "refine_schema"),
        ])
    
    # Always end with output generation
    task_definitions.extend([
        ("Generate SQL DDL script", "generate_sql"),
        ("Generate ERD diagram", "generate_erd"),
    ])
    
    return [create_task(content, node_name) for content, node_name in task_definitions]