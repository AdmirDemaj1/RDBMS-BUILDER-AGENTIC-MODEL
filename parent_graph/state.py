"""
Parent Graph State Management
Orchestrates Backend Builder and Enhancer subgraphs
"""
from typing import TypedDict, List, Optional, Dict, Any, Annotated
from enum import Enum
from datetime import datetime


# ============================================================
# ENUMS
# ============================================================

class WorkflowMode(str, Enum):
    """Workflow execution modes"""
    BUILD_ONLY = "build_only"
    BUILD_AND_ENHANCE = "build_and_enhance"
    ENHANCE_ONLY = "enhance_only"
    ITERATIVE = "iterative"


class EnhancementType(str, Enum):
    """Types of enhancements available"""
    ADD_FEATURE = "add_feature"
    OPTIMIZE_PERFORMANCE = "optimize_performance"
    ADD_SECURITY = "add_security"
    ADD_TESTING = "add_testing"
    REFACTOR_CODE = "refactor_code"
    ADD_DOCUMENTATION = "add_documentation"
    CUSTOM = "custom"


class SubgraphStatus(str, Enum):
    """Status of subgraph execution"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============================================================
# TYPE DEFINITIONS
# ============================================================

class EnhancementRequest(TypedDict):
    """User request for enhancement"""
    type: EnhancementType
    description: str
    target_modules: Optional[List[str]]
    priority: int
    requirements: Optional[str]


class EnhancementResult(TypedDict):
    """Result of enhancement execution"""
    request: EnhancementRequest
    status: SubgraphStatus
    changes: List[Dict[str, Any]]
    new_files: List[str]
    modified_files: List[str]
    error: Optional[str]


class SubgraphExecution(TypedDict):
    """Track subgraph execution"""
    name: str
    status: SubgraphStatus
    started_at: Optional[str]
    completed_at: Optional[str]
    llm_calls: int
    error: Optional[str]


# ============================================================
# STATE DEFINITIONS
# ============================================================

class ParentWorkingState(TypedDict):
    """Working state for parent graph"""
    mode: WorkflowMode
    current_subgraph: Optional[str]
    iteration_count: int
    max_iterations: int
    initial_requirements: str
    # Intent routing
    user_intent: Optional[str]  # "build" or "explain"
    intent_reasoning: Optional[str]
    # Enhancement and execution tracking
    enhancement_requests: List[EnhancementRequest]
    pending_enhancements: List[EnhancementRequest]
    subgraph_executions: List[SubgraphExecution]
    backend_state: Optional[Dict[str, Any]]
    enhancer_state: Optional[Dict[str, Any]]
    needs_user_input: bool
    is_complete: bool
    error: Optional[str]
    thread_id: Optional[str]
    parent_thread_id: Optional[str]
    builder_thread_id: Optional[str]
    enhancer_thread_id: Optional[str]


class ParentArchiveState(TypedDict):
    """Archive state for parent graph"""
    backend_results: Optional[Dict[str, Any]]
    enhancement_results: List[EnhancementResult]
    final_ddl_script: Optional[str]
    final_erd_diagram: Optional[str]
    final_nestjs_architecture: Optional[Dict[str, Any]]
    workflow_history: List[Dict[str, Any]]
    started_at: Optional[str]
    completed_at: Optional[str]
    total_llm_calls: int
    versions: List[Dict[str, Any]]


# ============================================================
# REDUCERS
# ============================================================

def merge_parent_working(left: ParentWorkingState, right: Dict[str, Any]) -> ParentWorkingState:
    """Merge parent working state updates"""
    if not left:
        return right
    if not right:
        return left
    
    merged = left.copy()
    for key, value in right.items():
        if value is not None:
            merged[key] = value
    return merged


def merge_parent_archive(left: ParentArchiveState, right: Dict[str, Any]) -> ParentArchiveState:
    """Merge parent archive state updates"""
    if not left:
        return right
    if not right:
        return left
    
    merged = left.copy()
    for key, value in right.items():
        if value is not None:
            if isinstance(value, list) and key in ['enhancement_results', 'workflow_history', 'versions']:
                merged[key] = merged.get(key, []) + value
            else:
                merged[key] = value
    return merged


# ============================================================
# GRAPH STATE
# ============================================================

class ParentGraphState(TypedDict):
    """Complete parent graph state"""
    working: Annotated[ParentWorkingState, merge_parent_working]
    archive: Annotated[ParentArchiveState, merge_parent_archive]


# ============================================================
# HELPERS
# ============================================================

def create_initial_parent_state(
    requirements: str,
    mode: WorkflowMode = WorkflowMode.BUILD_AND_ENHANCE,
    enhancements: Optional[List[EnhancementRequest]] = None,
    thread_id: Optional[str] = None
) -> ParentGraphState:
    """Create initial parent graph state"""
    import uuid
    
    thread_id = thread_id or str(uuid.uuid4())
    
    return {
        "working": {
            "mode": mode,
            "current_subgraph": None,
            "iteration_count": 0,
            "max_iterations": 5,
            "initial_requirements": requirements,
            "user_intent": None,
            "intent_reasoning": None,
            "enhancement_requests": enhancements or [],
            "pending_enhancements": (enhancements or []).copy(),
            "subgraph_executions": [],
            "backend_state": None,
            "enhancer_state": None,
            "needs_user_input": False,
            "is_complete": False,
            "error": None,
            "thread_id": thread_id,
            "parent_thread_id": thread_id,
            "builder_thread_id": f"{thread_id}-builder",
            "enhancer_thread_id": f"{thread_id}-enhancer"
        },
        "archive": {
            "backend_results": None,
            "enhancement_results": [],
            "final_ddl_script": None,
            "final_erd_diagram": None,
            "final_nestjs_architecture": None,
            "workflow_history": [],
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "total_llm_calls": 0,
            "versions": []
        }
    }