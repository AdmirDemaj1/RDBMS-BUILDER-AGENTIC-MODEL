# utils/thread_manager.py
"""
LangSmith Thread Management for multi-turn conversations.

This module provides utilities to group traces into threads, enabling
conversation history tracking and retrieval in LangSmith.

Usage:
    from utils.thread_manager import ThreadManager, create_thread_config
    
    # Create a new thread
    thread_id = ThreadManager.create_thread_id()
    
    # Get config for graph invocation
    config = create_thread_config(thread_id, project_name="my-project")
    
    # Invoke graph with thread tracking
    result = graph.invoke(state, config=config)
"""

import os
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from langsmith import Client


class ThreadManager:
    """Manages LangSmith threads for conversation tracking."""
    
    _client: Optional[Client] = None
    _default_project: Optional[str] = None
    
    @classmethod
    def initialize(cls, project_name: Optional[str] = None) -> None:
        """
        Initialize the ThreadManager with LangSmith client.
        
        Args:
            project_name: Default LangSmith project name. 
                         Falls back to LANGCHAIN_PROJECT env var.
        """
        cls._client = Client()
        cls._default_project = project_name or os.getenv("LANGCHAIN_PROJECT", "rdbms-builder")
    
    @classmethod
    def get_client(cls) -> Client:
        """Get or create the LangSmith client."""
        if cls._client is None:
            cls.initialize()
        return cls._client
    
    @classmethod
    def get_default_project(cls) -> str:
        """Get the default project name."""
        if cls._default_project is None:
            cls._default_project = os.getenv("LANGCHAIN_PROJECT", "rdbms-builder")
        return cls._default_project
    
    @staticmethod
    def create_thread_id() -> str:
        """
        Generate a new unique thread ID.
        
        Returns:
            A UUID string for the new thread.
        """
        return str(uuid.uuid4())
    
    @classmethod
    def get_thread_history(
        cls,
        thread_id: str,
        project_name: Optional[str] = None,
        run_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the history of runs for a specific thread.
        
        Args:
            thread_id: The thread ID to query.
            project_name: The LangSmith project name.
            run_type: Filter by run type (e.g., "llm", "chain", "tool").
            limit: Maximum number of runs to retrieve.
        
        Returns:
            List of run dictionaries sorted by start time (oldest first).
        """
        client = cls.get_client()
        project = project_name or cls.get_default_project()
        
        # Filter runs by thread metadata
        filter_string = (
            f'and(in(metadata_key, ["session_id","conversation_id","thread_id"]), '
            f'eq(metadata_value, "{thread_id}"))'
        )
        
        runs = []
        for run in client.list_runs(
            project_name=project,
            filter=filter_string,
            run_type=run_type,
            limit=limit
        ):
            runs.append({
                "id": str(run.id),
                "name": run.name,
                "run_type": run.run_type,
                "start_time": run.start_time,
                "end_time": run.end_time,
                "inputs": run.inputs,
                "outputs": run.outputs,
                "status": run.status,
                "error": run.error,
                "metadata": run.extra.get("metadata", {}) if run.extra else {}
            })
        
        # Sort by start time (oldest first for conversation order)
        runs.sort(key=lambda r: r["start_time"])
        return runs
    
    @classmethod
    def get_latest_run(
        cls,
        thread_id: str,
        project_name: Optional[str] = None,
        run_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent run for a thread.
        
        Args:
            thread_id: The thread ID to query.
            project_name: The LangSmith project name.
            run_type: Filter by run type.
        
        Returns:
            The most recent run dictionary or None if no runs found.
        """
        runs = cls.get_thread_history(
            thread_id=thread_id,
            project_name=project_name,
            run_type=run_type,
            limit=1
        )
        
        if runs:
            # Since we sorted oldest first, get the last one
            # Actually, let's re-query with proper sorting
            client = cls.get_client()
            project = project_name or cls.get_default_project()
            
            filter_string = (
                f'and(in(metadata_key, ["session_id","conversation_id","thread_id"]), '
                f'eq(metadata_value, "{thread_id}"))'
            )
            
            latest_runs = list(client.list_runs(
                project_name=project,
                filter=filter_string,
                run_type=run_type,
                limit=1
            ))
            
            if latest_runs:
                run = latest_runs[0]
                return {
                    "id": str(run.id),
                    "name": run.name,
                    "run_type": run.run_type,
                    "start_time": run.start_time,
                    "end_time": run.end_time,
                    "inputs": run.inputs,
                    "outputs": run.outputs,
                    "status": run.status,
                    "error": run.error,
                    "metadata": run.extra.get("metadata", {}) if run.extra else {}
                }
        
        return None
    
    @classmethod
    def list_threads(
        cls,
        project_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List all unique threads in a project.
        
        Args:
            project_name: The LangSmith project name.
            limit: Maximum number of threads to return.
        
        Returns:
            List of thread summaries with their latest activity.
        """
        client = cls.get_client()
        project = project_name or cls.get_default_project()
        
        # Get runs that have thread metadata
        filter_string = 'in(metadata_key, ["session_id","conversation_id","thread_id"])'
        
        threads: Dict[str, Dict[str, Any]] = {}
        
        for run in client.list_runs(
            project_name=project,
            filter=filter_string,
            limit=limit * 10  # Get more runs to find unique threads
        ):
            metadata = run.extra.get("metadata", {}) if run.extra else {}
            thread_id = (
                metadata.get("session_id") or 
                metadata.get("thread_id") or 
                metadata.get("conversation_id")
            )
            
            if thread_id and thread_id not in threads:
                threads[thread_id] = {
                    "thread_id": thread_id,
                    "first_seen": run.start_time,
                    "last_activity": run.start_time,
                    "run_count": 1
                }
            elif thread_id:
                threads[thread_id]["run_count"] += 1
                if run.start_time > threads[thread_id]["last_activity"]:
                    threads[thread_id]["last_activity"] = run.start_time
                if run.start_time < threads[thread_id]["first_seen"]:
                    threads[thread_id]["first_seen"] = run.start_time
        
        # Sort by last activity and limit
        thread_list = sorted(
            threads.values(),
            key=lambda t: t["last_activity"],
            reverse=True
        )[:limit]
        
        return thread_list


def create_thread_config(
    thread_id: str,
    project_name: Optional[str] = None,
    run_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    extra_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a LangGraph config with thread tracking metadata.
    
    This config should be passed to graph.invoke() to enable
    thread-based conversation tracking in LangSmith.
    
    Args:
        thread_id: Unique identifier for the conversation thread.
        project_name: LangSmith project name (optional).
        run_name: Custom name for this run (optional).
        tags: List of tags to attach to the run (optional).
        extra_metadata: Additional metadata to include (optional).
    
    Returns:
        Config dictionary for LangGraph invocation.
    
    Example:
        config = create_thread_config(
            thread_id="abc-123",
            project_name="my-project",
            run_name="Schema Generation",
            tags=["production"]
        )
        result = graph.invoke(state, config=config)
    """
    metadata = {
        "session_id": thread_id,  # Primary thread identifier
        "thread_id": thread_id,   # Alias for compatibility
    }
    
    if extra_metadata:
        metadata.update(extra_metadata)
    
    config: Dict[str, Any] = {
        "metadata": metadata,
        "configurable": {
            "thread_id": thread_id
        }
    }
    
    # Add run name if provided
    if run_name:
        config["run_name"] = run_name
    
    # Add tags if provided
    if tags:
        config["tags"] = tags
    
    # Add project name via callbacks config if provided
    if project_name:
        config["callbacks"] = {
            "project_name": project_name
        }
    
    return config


def get_or_create_thread_id(existing_thread_id: Optional[str] = None) -> str:
    """
    Get an existing thread ID or create a new one.
    
    Args:
        existing_thread_id: An existing thread ID to use, or None to create new.
    
    Returns:
        The thread ID to use.
    """
    if existing_thread_id:
        return existing_thread_id
    return ThreadManager.create_thread_id()

