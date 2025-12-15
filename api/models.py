"""
API Models - Pydantic schemas for request/response validation
Compatible with the NestJS client expectations
"""
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================
# ENUMS
# ============================================================

class WorkflowMode(str, Enum):
    """Workflow execution modes"""
    BUILD_ONLY = "build_only"
    BUILD_AND_ENHANCE = "build_and_enhance"
    ITERATIVE = "iterative"


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_INPUT = "awaiting_input"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================
# REQUEST MODELS
# ============================================================

class GenerateRequest(BaseModel):
    """Request body for /api/v1/generate and /api/v1/generate-async"""
    requirements: str = Field(..., description="User requirements for the database schema")
    mode: Optional[WorkflowMode] = Field(
        default=WorkflowMode.BUILD_ONLY,
        description="Workflow execution mode"
    )
    dialect: Optional[str] = Field(
        default="postgresql",
        description="SQL dialect (postgresql, mysql, sqlite)"
    )
    enable_critic: Optional[bool] = Field(
        default=True,
        description="Enable schema review by critic node"
    )
    generate_nestjs: Optional[bool] = Field(
        default=True,
        description="Generate NestJS backend architecture"
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Thread ID for conversation continuity"
    )
    enable_memory: Optional[bool] = Field(
        default=True,
        description="Enable long-term memory/checkpointing"
    )


class ResumeRequest(BaseModel):
    """Request body for /api/v1/resume"""
    thread_id: str = Field(..., description="Thread ID to resume")
    additional_requirements: Optional[str] = Field(
        default=None,
        description="Additional requirements to add to the conversation"
    )


class AnswerQuestionsRequest(BaseModel):
    """Request body for /api/v1/answer"""
    job_id: str = Field(..., description="Job ID for the current session")
    answers: List[str] = Field(
        ...,
        description="Answers in order matching the questions"
    )


# ============================================================
# RESPONSE MODELS
# ============================================================

class ResultsData(BaseModel):
    """Results data from graph execution"""
    ddl_script: Optional[str] = Field(default=None, description="Generated DDL SQL script")
    erd_diagram: Optional[str] = Field(default=None, description="Generated ERD diagram (Mermaid)")
    nestjs_architecture: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Generated NestJS architecture"
    )
    total_llm_calls: int = Field(default=0, description="Total LLM API calls made")
    versions: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Schema version history"
    )


class MetadataInfo(BaseModel):
    """Execution metadata"""
    mode: str = Field(..., description="Workflow mode used")
    iteration_count: int = Field(default=0, description="Number of iterations")
    is_complete: bool = Field(default=False, description="Whether execution completed")


class ClarifyingQuestion(BaseModel):
    """A clarifying question for the user"""
    question: str = Field(..., description="The question text")
    context: Optional[str] = Field(default=None, description="Context for the question")
    options: Optional[List[str]] = Field(default=None, description="Suggested answer options")


class GraphResult(BaseModel):
    """Standard response format for graph execution results"""
    success: bool = Field(..., description="Whether the operation succeeded")
    thread_id: Optional[str] = Field(default=None, description="Thread ID for this session")
    mode: Optional[str] = Field(default=None, description="Workflow mode used")
    results: Optional[ResultsData] = Field(default=None, description="Generated results")
    metadata: Optional[MetadataInfo] = Field(default=None, description="Execution metadata")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    traceback: Optional[str] = Field(default=None, description="Error traceback if failed")


class AsyncJobResponse(BaseModel):
    """Response for async job creation"""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    message: str = Field(..., description="Human-readable status message")


class JobStatusResponse(BaseModel):
    """Response for job status queries"""
    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Current job status")
    progress: float = Field(default=0, description="Progress percentage (0-100)")
    current_step: Optional[str] = Field(default=None, description="Current execution step")
    clarifying_questions: Optional[List[ClarifyingQuestion]] = Field(
        default=None,
        description="Questions requiring user input"
    )
    result: Optional[GraphResult] = Field(default=None, description="Final result when completed")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class ConversationInfo(BaseModel):
    """Information about a stored conversation"""
    thread_id: str = Field(..., description="Thread ID")
    checkpoint_count: int = Field(default=0, description="Number of checkpoints")
    latest_step: Optional[str] = Field(default=None, description="Latest step reached")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")


class ConversationsListResponse(BaseModel):
    """Response for listing conversations"""
    success: bool = Field(default=True)
    conversations: List[ConversationInfo] = Field(default_factory=list)
    total: int = Field(default=0, description="Total number of conversations")


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(default="healthy")
    version: str = Field(default="1.0.0")
    graph_ready: bool = Field(default=True)
    checkpointer_ready: bool = Field(default=True)


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = Field(default=False)
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")


class ResumeResponse(BaseModel):
    """Response for resume conversation - may include clarifying questions"""
    success: bool = Field(default=True)
    thread_id: str = Field(..., description="Thread ID for this session")
    job_id: Optional[str] = Field(default=None, description="Job ID if async processing started")
    status: str = Field(default="completed", description="Status: completed, awaiting_input")
    clarifying_questions: Optional[List[ClarifyingQuestion]] = Field(
        default=None,
        description="Questions requiring user input"
    )
    result: Optional[GraphResult] = Field(default=None, description="Final result when completed")
    message: Optional[str] = Field(default=None, description="Status message")

