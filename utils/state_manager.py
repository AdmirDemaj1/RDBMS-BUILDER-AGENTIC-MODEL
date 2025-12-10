# utils/state_manager.py
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from graph.state import (
    GraphState, Task, TaskStatus, CriticReport
)


class StateManager:
    
    @staticmethod
    def create_initial_state(
        requirements: str,
        dialect: str = "postgresql",
        enable_critic: bool = True,
        generate_nestjs: bool = True,
        thread_id: Optional[str] = None
    ) -> GraphState:
        """
        Create initial graph state with optional thread tracking.
        
        Args:
            requirements: User requirements for the database schema.
            dialect: SQL dialect (postgresql, mysql, sqlite).
            enable_critic: Whether to enable the critic node.
            generate_nestjs: Whether to generate NestJS architecture.
            thread_id: Optional thread ID for LangSmith conversation tracking.
                      If not provided, a new UUID will be generated.
        
        Returns:
            Initial GraphState dictionary.
        """
        # Generate thread_id if not provided
        if thread_id is None:
            thread_id = str(uuid.uuid4())
        
        return {
            "working": {
                "user_requirements": requirements,
                "sql_dialect": dialect,
                "enable_critic": enable_critic,
                "generate_nestjs": generate_nestjs,
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
                "max_iterations": 3,
                "needs_clarification": False,
                "is_complete": False,
                "error": None,
                "thread_id": thread_id
            },
            "archive": {
                "tasks": [],
                "clarifying_questions": [],
                "user_answers": [],
                "critic_reports": [],
                "ddl_script": "",
                "erd_diagram": "",
                "nestjs_architecture": None,
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "total_llm_calls": 0,
                "schema_versions": []
            }
        }
    
    @staticmethod
    def add_task(state: GraphState, task: Task) -> None:
        state["archive"]["tasks"].append(task)
        state["working"]["task_summary"].append({
            "id": task["id"],
            "node_name": task["node_name"],
            "status": task["status"]
        })
    
    @staticmethod
    def update_task_status(
        state: GraphState, 
        task_id: str, 
        status: TaskStatus, 
        result: str = None, 
        error: str = None
    ) -> None:
        for task in state["archive"]["tasks"]:
            if task["id"] == task_id:
                task["status"] = status
                if result:
                    task["result"] = result
                if error:
                    task["error"] = error
                break
        
        for summary in state["working"]["task_summary"]:
            if summary["id"] == task_id:
                summary["status"] = status
                break
    
    @staticmethod
    def get_task_by_node(state: GraphState, node_name: str) -> Optional[Task]:
        for task in state["archive"]["tasks"]:
            if task["node_name"] == node_name:
                return task
        return None
    
    @staticmethod
    def add_critic_report(state: GraphState, report: CriticReport) -> None:
        state["archive"]["critic_reports"].append(report)
        
        pending = [f for f in report["feedback_items"] if not f.get("applied")]
        critical = [f["issue"][:50] for f in pending if f["severity"] == "critical"]
        
        state["working"]["critic_summary"] = {
            "overall_score": report["overall_score"],
            "requires_revision": report["requires_revision"],
            "pending_issues_count": len(pending),
            "critical_issues": critical[:3]
        }
        
        if report["requires_revision"]:
            state["working"]["critic_revision_count"] += 1
    
    @staticmethod
    def get_pending_feedback(state: GraphState) -> List[Dict]:
        reports = state["archive"]["critic_reports"]
        if not reports:
            return []
        return [f for f in reports[-1].get("feedback_items", []) if not f.get("applied")]
    
    @staticmethod
    def mark_feedback_applied(state: GraphState) -> None:
        reports = state["archive"]["critic_reports"]
        if reports:
            for f in reports[-1].get("feedback_items", []):
                f["applied"] = True
            state["working"]["critic_summary"]["pending_issues_count"] = 0
            state["working"]["critic_summary"]["critical_issues"] = []
    
    @staticmethod
    def save_schema_version(state: GraphState, reason: str) -> None:
        tables = state["working"]["tables"]
        state["archive"]["schema_versions"].append({
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "table_count": len(tables),
            "table_names": [t["name"] for t in tables]
        })
    
    @staticmethod
    def increment_llm_calls(state: GraphState) -> None:
        state["archive"]["total_llm_calls"] += 1
    
    @staticmethod
    def add_user_answers(state: GraphState, answers: List[str]) -> None:
        state["archive"]["user_answers"] = answers
        if answers:
            state["working"]["user_requirements"] += "\n\nClarifications:\n" + "\n".join(answers)
        state["working"]["needs_clarification"] = False