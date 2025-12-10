# graph/state.py
from typing import TypedDict, List, Optional, Dict, Any
from enum import Enum


# ============================================================
# ENUMS
# ============================================================

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    SUGGESTION = "suggestion"


# ============================================================
# BASE TYPES
# ============================================================

class TaskSummary(TypedDict):
    id: str
    node_name: str
    status: TaskStatus


class Task(TypedDict):
    id: str
    content: str
    status: TaskStatus
    node_name: str
    result: Optional[str]
    error: Optional[str]


class CriticFeedback(TypedDict):
    target: str
    severity: str
    issue: str
    recommendation: str
    applied: bool


class CriticSummary(TypedDict):
    overall_score: int
    requires_revision: bool
    pending_issues_count: int
    critical_issues: List[str]


class CriticReport(TypedDict):
    overall_score: int
    feedback_items: List[CriticFeedback]
    summary: str
    requires_revision: bool


class Index(TypedDict):
    name: str
    columns: List[str]
    unique: bool
    type: str  # btree, hash, gin, gist


class ForeignKeyAction(TypedDict):
    on_delete: str  # CASCADE, SET NULL, RESTRICT, NO ACTION
    on_update: str


class Column(TypedDict):
    name: str
    data_type: str
    nullable: bool
    primary_key: bool
    unique: bool
    default: Optional[str]
    references: Optional[dict]
    check_constraint: Optional[str]
    is_encrypted: bool  # For sensitive data columns
    is_pii: bool  # Personal Identifiable Information flag


class Table(TypedDict):
    name: str
    description: str
    columns: List[Column]
    indexes: List[Index]
    constraints: List[str]  # CHECK, EXCLUDE constraints
    partitioning: Optional[dict]  # For large tables
    row_level_security: bool  # RLS enabled flag


class Entity(TypedDict):
    name: str
    description: str
    attributes: List[str]


class Relationship(TypedDict):
    from_entity: str
    to_entity: str
    type: str
    description: str


class ClarifyingQuestion(TypedDict):
    question: str
    context: str
    options: Optional[List[str]]


# ============================================================
# WORKING STATE (Hot Path)
# ============================================================

class WorkingState(TypedDict):
    user_requirements: str
    sql_dialect: str
    enable_critic: bool
    generate_nestjs: bool
    current_step: str
    current_task_id: Optional[str]
    task_summary: List[TaskSummary]
    entities: List[Entity]
    relationships: List[Relationship]
    tables: List[Table]
    critic_summary: Optional[CriticSummary]
    critic_revision_count: int
    max_critic_revisions: int
    validation_issues: List[str]
    iteration_count: int
    max_iterations: int
    needs_clarification: bool
    is_complete: bool
    error: Optional[str]
    # Thread tracking for LangSmith
    thread_id: Optional[str]


# ============================================================
# NESTJS ARCHITECTURE TYPES
# ============================================================

class NestJSModule(TypedDict):
    name: str
    entities: List[str]
    has_controller: bool
    has_service: bool
    has_repository: bool
    dependencies: List[str]


class NestJSEntity(TypedDict):
    name: str
    table_name: str
    columns: List[Dict[str, Any]]
    relations: List[Dict[str, Any]]


class NestJSEndpoint(TypedDict):
    method: str  # GET, POST, PUT, PATCH, DELETE
    path: str
    description: str
    request_dto: Optional[str]
    response_dto: Optional[str]


class NestJSDataFlowStep(TypedDict):
    step: int
    component: str
    action: str


class NestJSDataFlow(TypedDict):
    name: str
    trigger: str
    steps: List[NestJSDataFlowStep]


class NestJSGuardDetail(TypedDict):
    name: str
    purpose: str
    applies_to: List[str]


class NestJSInterceptorDetail(TypedDict):
    name: str
    purpose: str
    applies_to: List[str]


class NestJSArchitecture(TypedDict):
    project_name: str
    description: str
    modules: List[NestJSModule]
    entities: List[NestJSEntity]
    endpoints: List[NestJSEndpoint]
    shared_dtos: List[str]
    guards: List[str]
    interceptors: List[str]
    directory_structure: str
    module_diagram: str
    flow_diagrams: Dict[str, str]
    endpoint_table: str
    guards_detail: List[NestJSGuardDetail]
    interceptors_detail: List[NestJSInterceptorDetail]
    pipes: List[Dict[str, str]]
    middlewares: List[Dict[str, Any]]
    data_flows: List[NestJSDataFlow]
    environment_variables: List[str]
    external_integrations: List[str]
    code_samples: Dict[str, str]  # Empty - kept for compatibility


# ============================================================
# ARCHIVE STATE (Cold Storage)
# ============================================================

class ArchiveState(TypedDict):
    tasks: List[Task]
    clarifying_questions: List[ClarifyingQuestion]
    user_answers: List[str]
    critic_reports: List[CriticReport]
    ddl_script: str
    erd_diagram: str
    nestjs_architecture: Optional[NestJSArchitecture]
    started_at: Optional[str]
    completed_at: Optional[str]
    total_llm_calls: int
    schema_versions: List[Dict[str, Any]]


# ============================================================
# COMBINED STATE
# ============================================================

class GraphState(TypedDict):
    working: WorkingState
    archive: ArchiveState