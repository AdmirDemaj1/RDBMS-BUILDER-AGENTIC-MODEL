"""
Graph Service - Service layer for interacting with the LangGraph
Handles both sync and async graph execution
"""
import os
import uuid
import traceback
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from builder.graph.builder import get_compiled_graphs
from builder.graph.state import GraphState
from builder.utils.state_manager import StateManager
from builder.utils.checkpoint_manager import CheckpointManager, CheckpointerType
from builder.utils.thread_manager import create_thread_config

from api.job_manager import (
    JobManager, 
    Job, 
    JobStatus, 
    get_progress_for_step
)
from api.models import (
    GraphResult,
    ResultsData,
    MetadataInfo,
    ClarifyingQuestion,
    ConversationInfo
)


class GraphService:
    """
    Service class for interacting with the RDBMS Builder graph.
    Provides both synchronous and asynchronous execution methods.
    """
    
    def __init__(
        self,
        checkpoint_type: CheckpointerType = CheckpointerType.SQLITE,
        checkpoint_connection: Optional[str] = None
    ):
        self.checkpoint_type = checkpoint_type
        self.checkpoint_connection = checkpoint_connection or "./data/checkpoints.db"
        self._checkpoint_manager: Optional[CheckpointManager] = None
        self._checkpointer = None
    
    def _get_checkpoint_manager(self) -> CheckpointManager:
        """Get or create checkpoint manager"""
        if self._checkpoint_manager is None:
            self._checkpoint_manager = CheckpointManager(
                checkpointer_type=self.checkpoint_type,
                connection_string=self.checkpoint_connection
            )
        return self._checkpoint_manager
    
    def _get_checkpointer(self):
        """Get or create checkpointer"""
        if self._checkpointer is None:
            self._checkpointer = self._get_checkpoint_manager().create_checkpointer()
        return self._checkpointer
    
    def _create_initial_state(
        self,
        requirements: str,
        dialect: str = "postgresql",
        enable_critic: bool = True,
        generate_nestjs: bool = True,
        thread_id: Optional[str] = None
    ) -> GraphState:
        """Create initial graph state"""
        thread_id = thread_id or str(uuid.uuid4())
        return StateManager.create_initial_state(
            requirements=requirements,
            dialect=dialect,
            enable_critic=enable_critic,
            generate_nestjs=generate_nestjs,
            thread_id=thread_id
        )
    
    def _state_to_result(
        self,
        state: GraphState,
        thread_id: str,
        mode: str = "build_only"
    ) -> GraphResult:
        """Convert graph state to API result"""
        archive = state.get("archive", {})
        working = state.get("working", {})
        
        results = ResultsData(
            ddl_script=archive.get("ddl_script"),
            erd_diagram=archive.get("erd_diagram"),
            nestjs_architecture=archive.get("nestjs_architecture"),
            total_llm_calls=archive.get("total_llm_calls", 0),
            versions=archive.get("schema_versions"),
            formatted=archive.get("formatted_response")
        )
        
        metadata = MetadataInfo(
            mode=mode,
            iteration_count=working.get("iteration_count", 0),
            is_complete=working.get("is_complete", False)
        )
        
        return GraphResult(
            success=True,
            thread_id=thread_id,
            mode=mode,
            results=results,
            metadata=metadata
        )
    
    def run_sync(
        self,
        requirements: str,
        dialect: str = "postgresql",
        enable_critic: bool = True,
        generate_nestjs: bool = True,
        thread_id: Optional[str] = None,
        enable_memory: bool = True,
        mode: str = "build_only"
    ) -> GraphResult:
        """
        Run the graph synchronously.
        Returns the complete result when done.
        """
        thread_id = thread_id or str(uuid.uuid4())
        
        try:
            # Get checkpointer if memory enabled
            checkpointer = None
            if enable_memory:
                checkpointer = self._get_checkpointer()
            
            # Get compiled graphs
            graph_main, graph_cont = get_compiled_graphs(checkpointer)
            
            # Create initial state
            state = self._create_initial_state(
                requirements=requirements,
                dialect=dialect,
                enable_critic=enable_critic,
                generate_nestjs=generate_nestjs,
                thread_id=thread_id
            )
            
            # Check for existing checkpoint
            if enable_memory and checkpointer:
                try:
                    temp_config = CheckpointManager.create_thread_config(thread_id)
                    existing_tuple = checkpointer.get_tuple(temp_config)
                    if existing_tuple and existing_tuple.checkpoint:
                        existing_state = existing_tuple.checkpoint.get("channel_values")
                        if existing_state:
                            # Merge with existing state
                            state = existing_state
                            # Update requirements if new ones provided
                            if requirements:
                                state["working"]["user_requirements"] = requirements
                except Exception:
                    pass
            
            # Create config
            config = create_thread_config(
                thread_id=thread_id,
                run_name="API - Sync Generate"
            )
            if enable_memory:
                checkpoint_config = CheckpointManager.create_thread_config(thread_id)
                config.update(checkpoint_config)
            
            # Run the graph
            state = graph_main.invoke(state, config=config)
            
            # Handle clarification if needed
            if state["working"].get("needs_clarification"):
                questions = state["archive"].get("clarifying_questions", [])
                # Return with questions - client should call /answer endpoint
                return GraphResult(
                    success=True,
                    thread_id=thread_id,
                    mode=mode,
                    metadata=MetadataInfo(
                        mode=mode,
                        iteration_count=state["working"].get("iteration_count", 0),
                        is_complete=False
                    ),
                    error="Clarification needed - use /answer endpoint to provide answers"
                )
            
            return self._state_to_result(state, thread_id, mode)
            
        except Exception as e:
            return GraphResult(
                success=False,
                thread_id=thread_id,
                mode=mode,
                error=str(e),
                traceback=traceback.format_exc()
            )
    
    async def run_async(
        self,
        job: Job,
        job_manager: JobManager
    ) -> None:
        """
        Run the graph asynchronously.
        Updates job status as execution progresses.
        """
        try:
            await job_manager.update_job(
                job.job_id,
                status=JobStatus.PROCESSING,
                progress=5,
                current_step="initializing"
            )
            
            # Get checkpointer if memory enabled
            checkpointer = None
            if job.enable_memory:
                checkpointer = self._get_checkpointer()
            
            # Get compiled graphs
            graph_main, graph_cont = get_compiled_graphs(checkpointer)
            
            # Create initial state
            state = self._create_initial_state(
                requirements=job.requirements,
                dialect=job.dialect,
                enable_critic=job.enable_critic,
                generate_nestjs=job.generate_nestjs,
                thread_id=job.thread_id
            )
            
            await job_manager.update_job(
                job.job_id,
                progress=10,
                current_step="planning"
            )
            
            # Check for existing checkpoint
            if job.enable_memory and checkpointer:
                try:
                    temp_config = CheckpointManager.create_thread_config(job.thread_id)
                    existing_tuple = checkpointer.get_tuple(temp_config)
                    if existing_tuple and existing_tuple.checkpoint:
                        existing_state = existing_tuple.checkpoint.get("channel_values")
                        if existing_state:
                            state = existing_state
                            if job.requirements:
                                state["working"]["user_requirements"] = job.requirements
                except Exception:
                    pass
            
            # Create config
            config = create_thread_config(
                thread_id=job.thread_id,
                run_name="API - Async Generate"
            )
            if job.enable_memory:
                checkpoint_config = CheckpointManager.create_thread_config(job.thread_id)
                config.update(checkpoint_config)
            
            # Run graph in executor (it's blocking)
            state = await job_manager.run_in_executor(
                graph_main.invoke, state, config
            )
            
            # Check for clarification
            if state["working"].get("needs_clarification"):
                questions = state["archive"].get("clarifying_questions", [])
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
                    status=JobStatus.AWAITING_INPUT,
                    progress=15,
                    current_step="awaiting_clarification",
                    clarifying_questions=clarifying_questions,
                    state=state
                )
                return
            
            # Complete
            result = self._state_to_result(state, job.thread_id, "build_only")
            
            await job_manager.update_job(
                job.job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                current_step="complete",
                result=result.model_dump(),
                state=state
            )
            
        except Exception as e:
            await job_manager.update_job(
                job.job_id,
                status=JobStatus.FAILED,
                error=str(e),
                traceback_str=traceback.format_exc()
            )
    
    async def continue_with_answers(
        self,
        job: Job,
        answers: Dict[int, str],
        job_manager: JobManager
    ) -> None:
        """
        Continue graph execution after user provides answers.
        """
        try:
            await job_manager.update_job(
                job.job_id,
                status=JobStatus.PROCESSING,
                progress=20,
                current_step="processing_answers"
            )
            
            # Get stored state
            state = job.state
            if not state:
                raise ValueError("No state found for job - cannot continue")
            
            # Get checkpointer
            checkpointer = None
            if job.enable_memory:
                checkpointer = self._get_checkpointer()
            
            # Get continuation graph
            _, graph_cont = get_compiled_graphs(checkpointer)
            
            # Convert answers to expected format
            questions = state["archive"].get("clarifying_questions", [])
            answer_strings = []
            for idx, answer in answers.items():
                if idx < len(questions):
                    q = questions[idx]
                    answer_strings.append(f"Q: {q['question']} A: {answer}")
            
            # Update state with answers
            StateManager.add_user_answers(state, answer_strings)
            state["working"]["needs_clarification"] = False
            
            # Create config
            config = create_thread_config(
                thread_id=job.thread_id,
                run_name="API - Continue with Answers"
            )
            if job.enable_memory:
                checkpoint_config = CheckpointManager.create_thread_config(job.thread_id)
                config.update(checkpoint_config)
            
            await job_manager.update_job(
                job.job_id,
                progress=30,
                current_step="extracting_entities"
            )
            
            # Continue execution
            state = await job_manager.run_in_executor(
                graph_cont.invoke, state, config
            )
            
            # Complete
            result = self._state_to_result(state, job.thread_id, "build_only")
            
            await job_manager.update_job(
                job.job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                current_step="complete",
                result=result.model_dump(),
                state=state
            )
            
        except Exception as e:
            await job_manager.update_job(
                job.job_id,
                status=JobStatus.FAILED,
                error=str(e),
                traceback_str=traceback.format_exc()
            )
    
    def resume_conversation(
        self,
        thread_id: str,
        additional_requirements: Optional[str] = None
    ) -> Tuple[GraphResult, Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
        """
        Resume a previous conversation by thread ID.
        Uses LangGraph's native checkpoint resumption.
        
        Returns:
            Tuple of (result, clarifying_questions, state)
            - If clarifying_questions is not None, the client should answer them
            - state is included so it can be stored for continuation
        """
        try:
            checkpointer = self._get_checkpointer()
            config = CheckpointManager.create_thread_config(thread_id)
            
            # Get existing checkpoint to check current state
            existing_tuple = checkpointer.get_tuple(config)
            
            if not existing_tuple or not existing_tuple.checkpoint:
                return (
                    GraphResult(
                        success=False,
                        thread_id=thread_id,
                        error=f"No checkpoint found for thread {thread_id}"
                    ),
                    None,
                    None
                )
            
            state = existing_tuple.checkpoint.get("channel_values")
            if not state:
                return (
                    GraphResult(
                        success=False,
                        thread_id=thread_id,
                        error="Checkpoint exists but no state data found"
                    ),
                    None,
                    None
                )
            
            # Check if graph already completed
            if state["working"].get("is_complete"):
                if not additional_requirements:
                    return (self._state_to_result(state, thread_id, "build_only"), None, state)
            
            # Check if needs clarification - return questions for user to answer
            if state["working"].get("needs_clarification"):
                questions = state["archive"].get("clarifying_questions", [])
                return (
                    GraphResult(
                        success=True,
                        thread_id=thread_id,
                        mode="build_only",
                        metadata=MetadataInfo(
                            mode="build_only",
                            iteration_count=state["working"].get("iteration_count", 0),
                            is_complete=False
                        )
                    ),
                    questions,
                    state
                )
            
            # Get graph with checkpointer
            graph_main, _ = get_compiled_graphs(checkpointer)
            
            # Use LangGraph time-travel: get state history and find the right checkpoint
            # The checkpoint_id tells LangGraph exactly where to resume from
            states = list(graph_main.get_state_history(config))
            
            if not states:
                return (
                    GraphResult(
                        success=False,
                        thread_id=thread_id,
                        error="No state history found for this thread"
                    ),
                    None,
                    None
                )
            
            # Find the most recent checkpoint that has a next step (not completed)
            # States are returned in reverse chronological order
            resume_config = None
            for hist_state in states:
                if hist_state.next:  # Has next steps to execute
                    resume_config = hist_state.config
                    print(f"Resume: Found checkpoint at {hist_state.next}, checkpoint_id={resume_config['configurable'].get('checkpoint_id')}")
                    break
            
            if not resume_config:
                # Graph completed, return current results
                print("Resume: Graph already completed, returning results")
                return (self._state_to_result(state, thread_id, "build_only"), None, state)
            
            # Optional: Update state if additional requirements provided
            if additional_requirements:
                state["working"]["user_requirements"] += f"\n\nAdditional: {additional_requirements}"
                resume_config = graph_main.update_state(resume_config, values=state)
            
            # Resume execution from the checkpoint using time-travel
            # Pass None as input and the config with checkpoint_id
            state = graph_main.invoke(None, resume_config)
            
            # Check if clarification needed after run
            if state and state["working"].get("needs_clarification"):
                questions = state["archive"].get("clarifying_questions", [])
                return (
                    GraphResult(
                        success=True,
                        thread_id=thread_id,
                        mode="build_only",
                        metadata=MetadataInfo(
                            mode="build_only",
                            iteration_count=state["working"].get("iteration_count", 0),
                            is_complete=False
                        )
                    ),
                    questions,
                    state
                )
            
            return (self._state_to_result(state, thread_id, "build_only"), None, state)
            
        except Exception as e:
            return (
                GraphResult(
                    success=False,
                    thread_id=thread_id,
                    error=str(e),
                    traceback=traceback.format_exc()
                ),
                None,
                None
            )
    
    async def resume_async(
        self,
        job: Job,
        job_manager: JobManager,
        additional_requirements: Optional[str] = None
    ) -> None:
        """
        Resume a conversation asynchronously.
        Uses LangGraph's native checkpoint resumption.
        """
        try:
            await job_manager.update_job(
                job.job_id,
                status=JobStatus.PROCESSING,
                progress=5,
                current_step="loading_checkpoint"
            )
            
            checkpointer = self._get_checkpointer()
            config = CheckpointManager.create_thread_config(job.thread_id)
            
            # Get existing checkpoint
            existing_tuple = checkpointer.get_tuple(config)
            
            if not existing_tuple or not existing_tuple.checkpoint:
                await job_manager.update_job(
                    job.job_id,
                    status=JobStatus.FAILED,
                    error=f"No checkpoint found for thread {job.thread_id}"
                )
                return
            
            state = existing_tuple.checkpoint.get("channel_values")
            if not state:
                await job_manager.update_job(
                    job.job_id,
                    status=JobStatus.FAILED,
                    error="Checkpoint exists but no state data found"
                )
                return
            
            await job_manager.update_job(
                job.job_id,
                progress=10,
                current_step="checking_state"
            )
            
            # Check if already completed
            if state["working"].get("is_complete") and not additional_requirements:
                result = self._state_to_result(state, job.thread_id, "build_only")
                await job_manager.update_job(
                    job.job_id,
                    status=JobStatus.COMPLETED,
                    progress=100,
                    current_step="complete",
                    result=result.model_dump(),
                    state=state
                )
                return
            
            # Check if needs clarification
            if state["working"].get("needs_clarification"):
                questions = state["archive"].get("clarifying_questions", [])
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
                    status=JobStatus.AWAITING_INPUT,
                    progress=15,
                    current_step="awaiting_clarification",
                    clarifying_questions=clarifying_questions,
                    state=state
                )
                return
            
            # Get graph with checkpointer
            graph_main, _ = get_compiled_graphs(checkpointer)
            
            await job_manager.update_job(
                job.job_id,
                progress=20,
                current_step="finding_checkpoint"
            )
            
            # Use LangGraph time-travel: get state history and find the right checkpoint
            states = list(graph_main.get_state_history(config))
            
            if not states:
                await job_manager.update_job(
                    job.job_id,
                    status=JobStatus.FAILED,
                    error="No state history found for this thread"
                )
                return
            
            # Find the most recent checkpoint that has a next step (not completed)
            resume_config = None
            for hist_state in states:
                if hist_state.next:  # Has next steps to execute
                    resume_config = hist_state.config
                    print(f"Resume async: Found checkpoint at {hist_state.next}, checkpoint_id={resume_config['configurable'].get('checkpoint_id')}")
                    break
            
            if not resume_config:
                # Graph already completed, return results
                print("Resume async: Graph already completed, returning results")
                result = self._state_to_result(state, job.thread_id, "build_only")
                await job_manager.update_job(
                    job.job_id,
                    status=JobStatus.COMPLETED,
                    progress=100,
                    current_step="complete",
                    result=result.model_dump(),
                    state=state
                )
                return
            
            # Optional: Update state if additional requirements provided
            if additional_requirements:
                state["working"]["user_requirements"] += f"\n\nAdditional: {additional_requirements}"
                resume_config = graph_main.update_state(resume_config, values=state)
            
            await job_manager.update_job(
                job.job_id,
                progress=25,
                current_step="resuming_from_checkpoint"
            )
            
            # Resume execution from the checkpoint using time-travel
            state = await job_manager.run_in_executor(
                graph_main.invoke, None, resume_config
            )
            
            # Check if clarification needed
            if state and state["working"].get("needs_clarification"):
                questions = state["archive"].get("clarifying_questions", [])
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
                    status=JobStatus.AWAITING_INPUT,
                    progress=15,
                    current_step="awaiting_clarification",
                    clarifying_questions=clarifying_questions,
                    state=state
                )
                return
            
            # Complete
            result = self._state_to_result(state, job.thread_id, "build_only")
            
            await job_manager.update_job(
                job.job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                current_step="complete",
                result=result.model_dump(),
                state=state
            )
            
        except Exception as e:
            await job_manager.update_job(
                job.job_id,
                status=JobStatus.FAILED,
                error=str(e),
                traceback_str=traceback.format_exc()
            )
    
    def list_conversations(self, limit: int = 20) -> List[ConversationInfo]:
        """
        List stored conversations.
        """
        conversations = []
        
        try:
            if self.checkpoint_type == CheckpointerType.SQLITE:
                import sqlite3
                
                db_path = self.checkpoint_connection or "./data/checkpoints.db"
                if not os.path.exists(db_path):
                    return []
                
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        thread_id,
                        COUNT(*) as checkpoint_count,
                        MAX(json_extract(metadata, '$.step')) as latest_step
                    FROM checkpoints
                    GROUP BY thread_id
                    ORDER BY MAX(rowid) DESC
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                conn.close()
                
                for row in rows:
                    conversations.append(ConversationInfo(
                        thread_id=row[0],
                        checkpoint_count=row[1],
                        latest_step=row[2]
                    ))
        except Exception as e:
            print(f"Error listing conversations: {e}")
        
        return conversations
    
    def cleanup(self):
        """Cleanup resources"""
        if self._checkpoint_manager:
            self._checkpoint_manager._cleanup()


# Global service instance
_graph_service: Optional[GraphService] = None


def get_graph_service() -> GraphService:
    """Get or create global graph service instance"""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service

