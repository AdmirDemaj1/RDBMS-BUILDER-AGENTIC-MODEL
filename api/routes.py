"""
API Routes - FastAPI endpoints for the RDBMS Builder
Compatible with the NestJS client expectations
"""
import asyncio
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query

from api.models import (
    GenerateRequest,
    ResumeRequest,
    AnswerQuestionsRequest,
    ChatRequest,
    GraphResult,
    AsyncJobResponse,
    JobStatusResponse,
    ConversationsListResponse,
    HealthCheckResponse,
    ErrorResponse,
    ClarifyingQuestion,
    JobStatus,
    ResumeResponse,
    ChatResponse
)
from api.job_manager import JobManager, JobStatus as JobStatusEnum, _jobs_storage
from api.graph_service import get_graph_service, GraphService


logger = logging.getLogger(__name__)

# Create router with /api/v1 prefix
router = APIRouter(prefix="/api/v1", tags=["RDBMS Builder"])


def get_job_manager() -> JobManager:
    """Get job manager singleton"""
    return JobManager.get_instance()


# ============================================================
# HEALTH CHECK
# ============================================================

@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check",
    description="Check if the service is healthy and ready"
)
async def health_check():
    """Health check endpoint"""
    service = get_graph_service()
    
    # Check if checkpointer is ready
    checkpointer_ready = True
    try:
        _ = service._get_checkpointer()
    except Exception:
        checkpointer_ready = False
    
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        graph_ready=True,
        checkpointer_ready=checkpointer_ready
    )


# ============================================================
# SYNCHRONOUS GENERATION
# ============================================================

@router.post(
    "/generate",
    response_model=GraphResult,
    summary="Generate backend (sync)",
    description="Synchronously generate a complete backend architecture. May take several minutes."
)
async def generate_backend(request: GenerateRequest):
    """
    Synchronous backend generation.
    
    This endpoint blocks until generation is complete or clarification is needed.
    For long-running operations, consider using /generate-async instead.
    """
    service = get_graph_service()
    
    result = service.run_sync(
        requirements=request.requirements,
        dialect=request.dialect or "postgresql",
        enable_critic=request.enable_critic if request.enable_critic is not None else True,
        generate_nestjs=request.generate_nestjs if request.generate_nestjs is not None else True,
        thread_id=request.thread_id,
        enable_memory=request.enable_memory if request.enable_memory is not None else True,
        mode=request.mode.value if request.mode else "build_only"
    )
    
    if not result.success and result.error and "Clarification needed" not in result.error:
        raise HTTPException(status_code=500, detail=result.error)
    
    return result


# ============================================================
# ASYNCHRONOUS GENERATION
# ============================================================

@router.post(
    "/generate-async",
    response_model=AsyncJobResponse,
    summary="Generate backend (async)",
    description="Start async backend generation. Returns a job ID for status polling."
)
async def generate_backend_async(
    request: GenerateRequest,
    background_tasks: BackgroundTasks
):
    """
    Asynchronous backend generation.
    
    Returns immediately with a job_id. Use /job/{job_id} to poll for status.
    When clarification is needed, status will be 'awaiting_input'.
    Use /answer to provide answers and continue.
    """
    job_manager = get_job_manager()
    service = get_graph_service()
    
    # Create job
    job = await job_manager.create_job(
        requirements=request.requirements,
        dialect=request.dialect or "postgresql",
        enable_critic=request.enable_critic if request.enable_critic is not None else True,
        generate_nestjs=request.generate_nestjs if request.generate_nestjs is not None else True,
        thread_id=request.thread_id,
        enable_memory=request.enable_memory if request.enable_memory is not None else True
    )
    
    # Start background execution
    background_tasks.add_task(service.run_async, job, job_manager)
    
    return AsyncJobResponse(
        job_id=job.job_id,
        status="pending",
        message="Backend generation started. Poll /job/{job_id} for status."
    )


# ============================================================
# JOB STATUS
# ============================================================

@router.get(
    "/job/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status",
    description="Get the current status of an async job"
)
async def get_job_status(job_id: str):
    """
    Get the status of an async job.
    
    Possible statuses:
    - pending: Job created but not started
    - processing: Job is running
    - awaiting_input: Clarification questions need answers
    - completed: Job finished successfully
    - failed: Job failed with error
    """
    job_manager = get_job_manager()
    job = await job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Convert clarifying questions to response format
    clarifying_questions = None
    if job.clarifying_questions:
        clarifying_questions = [
            ClarifyingQuestion(
                question=q.get("question", ""),
                context=q.get("context"),
                options=q.get("options")
            )
            for q in job.clarifying_questions
        ]
    
    # Convert result dict to GraphResult if present
    result = None
    if job.result:
        result = GraphResult(**job.result)
    
    return JobStatusResponse(
        job_id=job.job_id,
        status=JobStatus(job.status.value),
        progress=job.progress,
        current_step=job.current_step,
        clarifying_questions=clarifying_questions,
        result=result,
        error=job.error
    )


# ============================================================
# ANSWER CLARIFYING QUESTIONS
# ============================================================

@router.post(
    "/answer",
    response_model=JobStatusResponse,
    summary="Answer clarifying questions",
    description="Provide answers to clarifying questions and continue generation"
)
async def answer_questions(
    request: AnswerQuestionsRequest,
    background_tasks: BackgroundTasks
):
    """
    Answer clarifying questions to continue generation.
    
    The answers should be a list of strings in order matching the questions.
    Example: ["Many-to-many", "Yes", "Role-based"]
    """
    job_manager = get_job_manager()
    service = get_graph_service()
    
    job = await job_manager.get_job(request.job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {request.job_id} not found")
    
    if job.status != JobStatusEnum.AWAITING_INPUT:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not awaiting input. Current status: {job.status.value}"
        )
    
    # Convert list to dict for internal processing
    answers_dict = {i: answer for i, answer in enumerate(request.answers)}
    
    # Update status
    await job_manager.update_job(
        job.job_id,
        status=JobStatusEnum.PROCESSING,
        progress=20,
        current_step="processing_answers",
        clarifying_questions=None
    )
    
    # Continue in background
    background_tasks.add_task(
        service.continue_with_answers,
        job,
        answers_dict,
        job_manager
    )
    
    # Return current status
    return JobStatusResponse(
        job_id=job.job_id,
        status=JobStatus.PROCESSING,
        progress=20,
        current_step="processing_answers"
    )


# ============================================================
# RESUME CONVERSATION
# ============================================================

@router.post(
    "/resume",
    response_model=ResumeResponse,
    summary="Resume conversation",
    description="Resume a previous conversation by thread ID. May return clarifying questions."
)
async def resume_conversation(
    request: ResumeRequest,
    background_tasks: BackgroundTasks
):
    """
    Resume a previous conversation.
    
    Loads the saved state from the checkpoint and optionally adds new requirements.
    If the graph needs clarification, returns questions with a job_id.
    Use /answer with the job_id to provide answers.
    """
    job_manager = get_job_manager()
    service = get_graph_service()
    
    result, questions, state = service.resume_conversation(
        thread_id=request.thread_id,
        additional_requirements=request.additional_requirements
    )
    
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)
    
    # If there are clarifying questions, create a job for answering
    if questions:
        logger.info(f"Resume requires clarification, creating job for thread {request.thread_id}")
        
        # Create a job to track the answers
        job = await job_manager.create_job(
            requirements=request.additional_requirements or "",
            thread_id=request.thread_id,
            enable_memory=True
        )
        
        logger.info(f"Created job {job.job_id} for resume clarification")
        
        # Store state in job
        clarifying_questions = [
            {
                "question": q.get("question", ""),
                "context": q.get("context"),
                "options": q.get("options")
            }
            for q in questions
        ]
        
        await job_manager.update_job(
            job.job_id,
            status=JobStatusEnum.AWAITING_INPUT,
            progress=15,
            current_step="awaiting_clarification",
            clarifying_questions=clarifying_questions,
            state=state
        )
        
        logger.info(f"Job {job.job_id} updated with state, returning response")
        
        # Verify job is stored
        verify_job = await job_manager.get_job(job.job_id)
        if not verify_job:
            logger.error(f"CRITICAL: Job {job.job_id} was created but not found in storage!")
        else:
            logger.info(f"Verified job {job.job_id} is in storage")
        
        return ResumeResponse(
            success=True,
            thread_id=request.thread_id,
            job_id=job.job_id,
            status="awaiting_input",
            clarifying_questions=[
                ClarifyingQuestion(
                    question=q.get("question", ""),
                    context=q.get("context"),
                    options=q.get("options")
                )
                for q in questions
            ],
            message="Clarification needed. Use /answer endpoint with the job_id to provide answers."
        )
    
    # No questions, return completed result
    return ResumeResponse(
        success=True,
        thread_id=request.thread_id,
        status="completed",
        result=result
    )


@router.post(
    "/resume-async",
    response_model=AsyncJobResponse,
    summary="Resume conversation (async)",
    description="Resume a previous conversation asynchronously. Returns a job ID for status polling."
)
async def resume_conversation_async(
    request: ResumeRequest,
    background_tasks: BackgroundTasks
):
    """
    Resume a conversation asynchronously.
    
    Returns immediately with a job_id. Use /job/{job_id} to poll for status.
    When clarification is needed, status will be 'awaiting_input'.
    Use /answer to provide answers and continue.
    """
    job_manager = get_job_manager()
    service = get_graph_service()
    
    # Create job
    job = await job_manager.create_job(
        requirements=request.additional_requirements or "",
        thread_id=request.thread_id,
        enable_memory=True
    )
    
    # Start background execution
    background_tasks.add_task(
        service.resume_async,
        job,
        job_manager,
        request.additional_requirements
    )
    
    return AsyncJobResponse(
        job_id=job.job_id,
        status="pending",
        message="Resume started. Poll /job/{job_id} for status."
    )


# ============================================================
# LIST CONVERSATIONS
# ============================================================

@router.get(
    "/conversations",
    response_model=ConversationsListResponse,
    summary="List conversations",
    description="Get a list of all stored conversations"
)
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum conversations to return")
):
    """
    List all stored conversations.
    
    Returns conversation thread IDs with their checkpoint counts.
    """
    service = get_graph_service()
    conversations = service.list_conversations(limit=limit)
    
    return ConversationsListResponse(
        success=True,
        conversations=conversations,
        total=len(conversations)
    )


# ============================================================
# ADDITIONAL UTILITY ENDPOINTS
# ============================================================

@router.get(
    "/conversation/{thread_id}",
    response_model=GraphResult,
    summary="Get conversation details",
    description="Get the current state of a specific conversation"
)
async def get_conversation_details(thread_id: str):
    """
    Get details of a specific conversation.
    
    Loads the latest checkpoint state for the given thread ID.
    """
    service = get_graph_service()
    result, questions, state = service.resume_conversation(thread_id=thread_id)
    
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)
    
    return result


@router.get(
    "/debug/jobs",
    summary="List all jobs (debug)",
    description="Debug endpoint to list all jobs in memory"
)
async def debug_list_jobs():
    """
    Debug endpoint to list all jobs currently in memory.
    """
    jobs_info = []
    for job_id, job in _jobs_storage.items():
        jobs_info.append({
            "job_id": job_id,
            "thread_id": job.thread_id,
            "status": job.status.value,
            "current_step": job.current_step,
            "progress": job.progress,
            "created_at": job.created_at.isoformat(),
            "has_state": job.state is not None
        })
    
    return {
        "total_jobs": len(_jobs_storage),
        "jobs": jobs_info
    }


# ============================================================
# CHAT - AUTO-ROUTING ENDPOINT (uses parent graph)
# ============================================================

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with auto-routing",
    description="Auto-routes between build and explain based on user intent. Use this for interactive conversations."
)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks
):
    """
    Chat endpoint with automatic intent routing.
    
    The parent graph analyzes your message and decides:
    - **build**: Creates a new backend or modifies existing one
    - **explain**: Answers questions about the generated backend
    
    For explain mode, you MUST provide a thread_id of an existing conversation
    that has a generated backend.
    
    Examples:
    - "Build me a hotel management system" → build mode
    - "What tables were created?" → explain mode (requires thread_id)
    - "Explain the relationships in the schema" → explain mode
    """
    from parent_graph.builder import classify_intent
    from explainer.run_explainer import run_explainer
    import uuid
    
    job_manager = get_job_manager()
    service = get_graph_service()
    
    # Use parent graph's intent classifier
    has_backend = False
    backend_context = None
    
    # If thread_id provided, check if backend exists
    if request.thread_id:
        result, _, state = service.resume_conversation(thread_id=request.thread_id)
        if result.success and state:
            archive = state.get("archive", {})
            if archive.get("ddl_script") or archive.get("nestjs_architecture"):
                has_backend = True
                backend_context = {
                    "ddl_script": archive.get("ddl_script"),
                    "erd_diagram": archive.get("erd_diagram"),
                    "nestjs_architecture": archive.get("nestjs_architecture"),
                    "working": state.get("working", {})
                }
    
    # Classify intent using parent graph's LLM classifier
    classification = classify_intent(request.message, has_backend=has_backend)
    
    thread_id = request.thread_id or str(uuid.uuid4())
    
    logger.info(f"Chat intent: {classification.intent} - {classification.reasoning}")
    
    # Route based on intent
    if classification.intent == "explain":
        if not has_backend:
            return ChatResponse(
                success=False,
                thread_id=thread_id,
                intent="explain",
                intent_reasoning=classification.reasoning,
                status="error",
                message="No backend found. Please provide a thread_id of an existing conversation with a generated backend, or build one first."
            )
        
        # Run explainer synchronously (it's usually fast)
        explanation = run_explainer(
            user_question=request.message,
            backend_context=backend_context,
            interactive=False
        )
        
        return ChatResponse(
            success=True,
            thread_id=thread_id,
            intent="explain",
            intent_reasoning=classification.reasoning,
            explanation=explanation,
            status="completed",
            message="Question answered based on the generated backend."
        )
    
    else:  # build intent
        # Start async build job
        job = await job_manager.create_job(
            requirements=request.message,
            dialect=request.dialect or "postgresql",
            enable_critic=request.enable_critic if request.enable_critic is not None else True,
            generate_nestjs=request.generate_nestjs if request.generate_nestjs is not None else True,
            thread_id=thread_id,
            enable_memory=True
        )
        
        # Start background execution
        background_tasks.add_task(service.run_async, job, job_manager)
        
        return ChatResponse(
            success=True,
            thread_id=thread_id,
            intent="build",
            intent_reasoning=classification.reasoning,
            job_id=job.job_id,
            status="processing",
            message=f"Build started. Poll /job/{job.job_id} for status."
        )


@router.post(
    "/explain",
    response_model=ChatResponse,
    summary="Ask questions about generated backend",
    description="Directly query the explainer about an existing backend. Requires thread_id."
)
async def explain_backend(
    request: ChatRequest
):
    """
    Direct endpoint for asking questions about a generated backend.
    
    Unlike /chat, this always uses explain mode without intent classification.
    Requires a thread_id of a conversation that has generated a backend.
    """
    from explainer.run_explainer import run_explainer
    import uuid
    
    service = get_graph_service()
    
    if not request.thread_id:
        raise HTTPException(
            status_code=400,
            detail="thread_id is required for explain endpoint. Use the thread_id from a previous build."
        )
    
    # Load backend context
    result, _, state = service.resume_conversation(thread_id=request.thread_id)
    
    if not result.success:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {result.error}")
    
    if not state:
        raise HTTPException(status_code=404, detail="No state found for this conversation")
    
    archive = state.get("archive", {})
    if not archive.get("ddl_script") and not archive.get("nestjs_architecture"):
        raise HTTPException(
            status_code=400,
            detail="No backend has been generated for this conversation yet. Run a build first."
        )
    
    backend_context = {
        "ddl_script": archive.get("ddl_script"),
        "erd_diagram": archive.get("erd_diagram"),
        "nestjs_architecture": archive.get("nestjs_architecture"),
        "working": state.get("working", {})
    }
    
    # Run explainer
    explanation = run_explainer(
        user_question=request.message,
        backend_context=backend_context,
        interactive=False
    )
    
    return ChatResponse(
        success=True,
        thread_id=request.thread_id,
        intent="explain",
        explanation=explanation,
        status="completed",
        message="Question answered."
    )

