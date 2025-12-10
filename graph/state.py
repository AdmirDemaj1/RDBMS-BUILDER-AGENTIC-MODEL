# graph/state.py
from typing import TypedDict, List, Optional
from enum import Enum


class TaskStatus(str, Enum):
    """Status of a task in the execution plan."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Task(TypedDict):
    """Represents a single task in the execution plan."""
    id: str
    content: str
    status: TaskStatus
    node_name: str
    result: Optional[str]
    error: Optional[str]


class CriticFeedback(TypedDict):
    """Feedback from the critic agent."""
    target: str  # What is being critiqued (entities, relationships, schema)
    severity: str  # "critical", "warning", "suggestion"
    issue: str  # Description of the issue
    recommendation: str  # How to fix it
    applied: bool  # Whether the fix was applied


class CriticReport(TypedDict):
    """Complete critic evaluation report."""
    overall_score: int  # 1-10
    feedback_items: List[CriticFeedback]
    summary: str
    requires_revision: bool


class Column(TypedDict):
    """Represents a database column."""
    name: str
    data_type: str
    nullable: bool
    primary_key: bool
    unique: bool
    default: Optional[str]
    references: Optional[dict]


class Table(TypedDict):
    """Represents a database table."""
    name: str
    description: str
    columns: List[Column]
    indexes: List[dict]


class Entity(TypedDict):
    """Raw entity extracted from user input."""
    name: str
    description: str
    attributes: List[str]


class Relationship(TypedDict):
    """Relationship between entities."""
    from_entity: str
    to_entity: str
    type: str
    description: str


class ClarifyingQuestion(TypedDict):
    """A question to ask the user."""
    question: str
    context: str
    options: Optional[List[str]]


class GraphState(TypedDict):
    """
    The complete state that flows through our graph.
    """
    # ===== Input =====
    user_requirements: str
    user_answers: List[str]
    
    # ===== Configuration =====
    sql_dialect: str
    enable_critic: bool  # Whether to run critic evaluations
    
    # ===== Planning & Progress =====
    tasks: List[Task]
    current_task_id: Optional[str]
    
    # ===== Clarification =====
    clarifying_questions: List[ClarifyingQuestion]
    needs_clarification: bool
    
    # ===== Extracted Information =====
    entities: List[Entity]
    relationships: List[Relationship]
    
    # ===== Generated Schema =====
    tables: List[Table]
    
    # ===== Critic Evaluation =====
    critic_reports: List[CriticReport]
    critic_revision_count: int
    max_critic_revisions: int
    
    # ===== Validation =====
    validation_issues: List[str]
    iteration_count: int
    max_iterations: int
    
    # ===== Output =====
    ddl_script: str
    erd_diagram: str
    
    # ===== Control Flow =====
    current_step: str
    is_complete: bool
    error: Optional[str]