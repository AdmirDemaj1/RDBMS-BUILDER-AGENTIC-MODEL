# utils/task_manager.py
from typing import List, Optional
from ..graph.state import GraphState, Task, TaskStatus
from .state_manager import StateManager
import uuid


def create_task(content: str, node_name: str) -> Task:
    return {
        "id": str(uuid.uuid4())[:8],
        "content": content,
        "status": TaskStatus.PENDING,
        "node_name": node_name,
        "result": None,
        "error": None
    }


def start_task(state: GraphState, node_name: str) -> None:
    task = StateManager.get_task_by_node(state, node_name)
    if task:
        print(f"\n{'='*50}")
        print(f"🔄 {task['content']}")
        print(f"{'='*50}")
        StateManager.update_task_status(state, task["id"], TaskStatus.IN_PROGRESS)
        state["working"]["current_task_id"] = task["id"]


def complete_task(state: GraphState, node_name: str, result: str) -> None:
    task = StateManager.get_task_by_node(state, node_name)
    if task:
        StateManager.update_task_status(state, task["id"], TaskStatus.COMPLETED, result=result)
        
        tasks = state["archive"]["tasks"]
        completed = sum(1 for t in tasks if t["status"] == TaskStatus.COMPLETED)
        total = len(tasks)
        pct = (completed / total * 100) if total else 0
        
        print(f"✅ Done: {result}")
        print(f"📊 Progress: {completed}/{total} ({pct:.0f}%)")
        print_progress_bar(completed, total)
        
        state["working"]["current_task_id"] = None


def fail_task(state: GraphState, node_name: str, error: str) -> None:
    task = StateManager.get_task_by_node(state, node_name)
    if task:
        StateManager.update_task_status(state, task["id"], TaskStatus.FAILED, error=error)
        print(f"❌ Failed: {error}")
        state["working"]["current_task_id"] = None
        state["working"]["error"] = error


def skip_task(state: GraphState, node_name: str, reason: str) -> None:
    task = StateManager.get_task_by_node(state, node_name)
    if task:
        StateManager.update_task_status(state, task["id"], TaskStatus.SKIPPED, result=f"Skipped: {reason}")
        print(f"⏭️ Skipped: {reason}")
        state["working"]["current_task_id"] = None


def print_progress_bar(completed: int, total: int, width: int = 40) -> None:
    if total == 0:
        return
    filled = int(width * completed / total)
    bar = "█" * filled + "░" * (width - filled)
    print(f"   [{bar}]")


def print_task_summary(state: GraphState) -> None:
    tasks = state["archive"]["tasks"]
    
    print("\n" + "=" * 50)
    print("📋 TASK SUMMARY")
    print("=" * 50)
    
    icons = {
        TaskStatus.PENDING: "⏳",
        TaskStatus.IN_PROGRESS: "🔄",
        TaskStatus.COMPLETED: "✅",
        TaskStatus.FAILED: "❌",
        TaskStatus.SKIPPED: "⏭️"
    }
    
    for i, task in enumerate(tasks, 1):
        icon = icons.get(task["status"], "❓")
        print(f"{i}. {icon} {task['content'][:50]}")
        if task.get("result"):
            print(f"      └─ {task['result'][:60]}")
    
    completed = sum(1 for t in tasks if t["status"] == TaskStatus.COMPLETED)
    failed = sum(1 for t in tasks if t["status"] == TaskStatus.FAILED)
    
    print("-" * 50)
    print(f"Total: {len(tasks)} | ✅ {completed} | ❌ {failed}")
    print("=" * 50)


def get_default_tasks(enable_critic: bool = True, generate_nestjs: bool = True) -> List[Task]:
    defs = [
        ("Analyze requirements", "clarify"),
        ("Extract entities", "extract_entities"),
        ("Analyze relationships", "analyze_relationships"),
        ("Design schema", "design_schema"),
        ("Validate schema", "validate_schema"),
    ]
    
    if enable_critic:
        defs.extend([
            ("Critic evaluation", "critic"),
            ("Refine schema", "refine_schema"),
        ])
    
    defs.extend([
        ("Generate SQL DDL", "generate_sql"),
        ("Generate ERD", "generate_erd"),
    ])
    
    if generate_nestjs:
        defs.append(("Generate NestJS architecture", "generate_nestjs"))
    
    return [create_task(content, node) for content, node in defs]