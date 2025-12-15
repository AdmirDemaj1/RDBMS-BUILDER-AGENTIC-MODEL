"""
Job Manager - Handles async job execution and tracking
Manages background graph execution with status updates
"""
import asyncio
import uuid
import traceback
import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor


logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_INPUT = "awaiting_input"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """Represents an async job"""
    job_id: str
    thread_id: str
    status: JobStatus = JobStatus.PENDING
    progress: float = 0
    current_step: str = "initialized"
    clarifying_questions: Optional[List[Dict[str, Any]]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    traceback_str: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Store the graph state for continuation
    state: Optional[Dict[str, Any]] = None
    
    # Request parameters
    requirements: str = ""
    dialect: str = "postgresql"
    enable_critic: bool = True
    generate_nestjs: bool = True
    enable_memory: bool = True


# Module-level storage for true singleton behavior
_jobs_storage: Dict[str, Job] = {}
_storage_lock = threading.Lock()


class JobManager:
    """
    Manages async job execution for the graph.
    Uses ThreadPoolExecutor for running blocking graph operations.
    Jobs are stored at module level to ensure persistence across instances.
    """
    
    _instance: Optional["JobManager"] = None
    _init_lock = threading.Lock()
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._async_lock: Optional[asyncio.Lock] = None
    
    def _get_async_lock(self) -> asyncio.Lock:
        """Get or create async lock for current event loop"""
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock
    
    @classmethod
    def get_instance(cls) -> "JobManager":
        """Get singleton instance of JobManager"""
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = cls()
                logger.info("JobManager singleton created")
            return cls._instance
    
    @property
    def jobs(self) -> Dict[str, Job]:
        """Access module-level jobs storage"""
        return _jobs_storage
    
    async def create_job(
        self,
        requirements: str,
        dialect: str = "postgresql",
        enable_critic: bool = True,
        generate_nestjs: bool = True,
        thread_id: Optional[str] = None,
        enable_memory: bool = True
    ) -> Job:
        """Create a new job"""
        job_id = str(uuid.uuid4())
        thread_id = thread_id or str(uuid.uuid4())
        
        job = Job(
            job_id=job_id,
            thread_id=thread_id,
            requirements=requirements,
            dialect=dialect,
            enable_critic=enable_critic,
            generate_nestjs=generate_nestjs,
            enable_memory=enable_memory
        )
        
        # Use thread-safe storage
        with _storage_lock:
            _jobs_storage[job_id] = job
            logger.info(f"Job created: {job_id} (total jobs: {len(_jobs_storage)})")
        
        return job
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        with _storage_lock:
            job = _jobs_storage.get(job_id)
            if job:
                logger.debug(f"Job found: {job_id}")
            else:
                logger.warning(f"Job not found: {job_id} (available: {list(_jobs_storage.keys())})")
            return job
    
    async def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[float] = None,
        current_step: Optional[str] = None,
        clarifying_questions: Optional[List[Dict[str, Any]]] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        traceback_str: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None
    ) -> Optional[Job]:
        """Update job status and data"""
        with _storage_lock:
            job = _jobs_storage.get(job_id)
            if not job:
                logger.warning(f"Cannot update job {job_id}: not found")
                return None
            
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = progress
            if current_step is not None:
                job.current_step = current_step
            if clarifying_questions is not None:
                job.clarifying_questions = clarifying_questions
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            if traceback_str is not None:
                job.traceback_str = traceback_str
            if state is not None:
                job.state = state
            
            job.updated_at = datetime.utcnow()
            logger.debug(f"Job updated: {job_id} -> {job.status.value}")
            return job
    
    def run_in_executor(self, func, *args, **kwargs):
        """Run a blocking function in the thread pool executor"""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(
            self.executor,
            lambda: func(*args, **kwargs)
        )
    
    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove jobs older than max_age_hours"""
        cutoff = datetime.utcnow()
        with _storage_lock:
            to_remove = []
            for job_id, job in _jobs_storage.items():
                age = (cutoff - job.created_at).total_seconds() / 3600
                if age > max_age_hours and job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                    to_remove.append(job_id)
            
            for job_id in to_remove:
                del _jobs_storage[job_id]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old jobs")
    
    def shutdown(self):
        """Shutdown the executor"""
        self.executor.shutdown(wait=True)


# Progress tracking steps with percentages
STEP_PROGRESS = {
    "initialized": 0,
    "planning": 5,
    "clarifying": 10,
    "extracting_entities": 20,
    "analyzing_relationships": 30,
    "designing_schema": 40,
    "verifying_initial_schema": 45,
    "validating_schema": 50,
    "critic_review": 60,
    "refining_schema": 70,
    "verifying_refinements": 75,
    "generating_sql": 80,
    "generating_erd": 85,
    "generating_nestjs": 90,
    "aggregating": 95,
    "complete": 100
}


def get_progress_for_step(step: str) -> float:
    """Get progress percentage for a given step"""
    # Normalize step name
    step_lower = step.lower().replace(" ", "_").replace("-", "_")
    
    # Direct match
    if step_lower in STEP_PROGRESS:
        return STEP_PROGRESS[step_lower]
    
    # Partial match
    for key, value in STEP_PROGRESS.items():
        if key in step_lower or step_lower in key:
            return value
    
    # Default
    return 50

