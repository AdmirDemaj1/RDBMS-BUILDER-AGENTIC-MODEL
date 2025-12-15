# utils/checkpoint_manager.py
"""
LangGraph Checkpointing Manager for Long-Term Memory Persistence

This module provides utilities for managing checkpoints in LangGraph, enabling:
- Long-term memory across sessions
- Error recovery and fault tolerance
- Human-in-the-loop workflows
- Time travel debugging and state replay
"""

import os
from typing import Optional, Dict, Any, List
from enum import Enum
from contextlib import contextmanager

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.checkpoint.memory import MemorySaver
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False
    SqliteSaver = None
    MemorySaver = None

try:
    from langgraph.checkpoint.postgres import PostgresSaver
    import psycopg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    PostgresSaver = None


class CheckpointerType(str, Enum):
    """Supported checkpointer types for persistence."""
    MEMORY = "memory"  # In-memory (not persistent, for testing)
    SQLITE = "sqlite"  # SQLite database (local persistence)
    POSTGRES = "postgres"  # PostgreSQL database (production)


class CheckpointManager:
    """
    Manages LangGraph checkpointing for long-term memory persistence.
    
    Features:
    - Multiple backend support (Memory, SQLite, PostgreSQL)
    - Automatic connection management
    - Thread-based session tracking
    - State history and retrieval
    """
    
    def __init__(
        self,
        checkpointer_type: CheckpointerType = CheckpointerType.SQLITE,
        connection_string: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the checkpoint manager.
        
        Args:
            checkpointer_type: Type of checkpointer to use
            connection_string: Database connection string (for SQLite/PostgreSQL)
                             - SQLite: Path to database file (e.g., "./checkpoints.db")
                             - PostgreSQL: Connection URI (e.g., "postgresql://user:pass@localhost/db")
            **kwargs: Additional arguments for the checkpointer
        """
        self.checkpointer_type = checkpointer_type
        self.connection_string = connection_string or self._get_default_connection()
        self.kwargs = kwargs
        self._checkpointer = None
        self._conn = None
        
        # Validate dependencies
        self._validate_dependencies()
    
    def _validate_dependencies(self):
        """Validate that required dependencies are installed."""
        if self.checkpointer_type == CheckpointerType.SQLITE and not SQLITE_AVAILABLE:
            raise ImportError(
                "SQLite checkpointer not available. Install with: "
                "pip install langgraph-checkpoint-sqlite"
            )
        
        if self.checkpointer_type == CheckpointerType.POSTGRES and not POSTGRES_AVAILABLE:
            raise ImportError(
                "PostgreSQL checkpointer not available. Install with: "
                "pip install langgraph-checkpoint-postgres psycopg"
            )
        
        if self.checkpointer_type == CheckpointerType.MEMORY and not SQLITE_AVAILABLE:
            raise ImportError(
                "Memory checkpointer not available. Install with: "
                "pip install langgraph"
            )
    
    def _get_default_connection(self) -> str:
        """Get default connection string based on checkpointer type."""
        if self.checkpointer_type == CheckpointerType.SQLITE:
            # Default to local SQLite file
            return "./data/checkpoints.db"
        elif self.checkpointer_type == CheckpointerType.POSTGRES:
            # Try to get from environment variable
            return os.getenv(
                "POSTGRES_CHECKPOINT_URI",
                "postgresql://localhost:5432/rdbms_builder"
            )
        return ""
    
    @contextmanager
    def get_checkpointer(self):
        """
        Context manager for checkpointer lifecycle.
        
        Yields:
            Checkpointer instance (MemorySaver, SqliteSaver, or PostgresSaver)
        
        Example:
            with checkpoint_manager.get_checkpointer() as checkpointer:
                graph = builder.compile(checkpointer=checkpointer)
                result = graph.invoke(input_data, config=config)
        """
        try:
            self._checkpointer = self._create_checkpointer()
            yield self._checkpointer
        finally:
            self._cleanup()
    
    def create_checkpointer(self):
        """
        Create and return a checkpointer instance.
        
        This is a public method that creates the checkpointer without context manager.
        Use this when you need direct access to the checkpointer object.
        
        Returns:
            Checkpointer instance (MemorySaver, SqliteSaver, or PostgresSaver)
        """
        return self._create_checkpointer()
    
    def _create_checkpointer(self):
        """Create and initialize the checkpointer (internal method)."""
        if self.checkpointer_type == CheckpointerType.MEMORY:
            return MemorySaver()
        
        elif self.checkpointer_type == CheckpointerType.SQLITE:
            # Ensure directory exists
            db_path = self.connection_string
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
            
            # Create SQLite checkpointer with connection
            # SqliteSaver.from_conn_string returns a context manager
            # We need to enter it to get the actual checkpointer
            context_manager = SqliteSaver.from_conn_string(db_path)
            checkpointer = context_manager.__enter__()
            # Store context manager for cleanup
            self._conn = context_manager
            return checkpointer
        
        elif self.checkpointer_type == CheckpointerType.POSTGRES:
            # Create PostgreSQL checkpointer
            # PostgresSaver.from_conn_string returns a context manager
            context_manager = PostgresSaver.from_conn_string(self.connection_string)
            checkpointer = context_manager.__enter__()
            # Store context manager for cleanup
            self._conn = context_manager
            return checkpointer
        
        else:
            raise ValueError(f"Unsupported checkpointer type: {self.checkpointer_type}")
    
    def _cleanup(self):
        """Cleanup resources."""
        if self._conn:
            try:
                # If _conn is a context manager, exit it properly
                if hasattr(self._conn, '__exit__'):
                    self._conn.__exit__(None, None, None)
                else:
                    self._conn.close()
            except Exception:
                pass
            self._conn = None
        
        self._checkpointer = None
    
    @staticmethod
    def create_thread_config(
        thread_id: str,
        checkpoint_ns: Optional[str] = None,
        checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a configuration dict for thread-based checkpointing.
        
        Args:
            thread_id: Unique identifier for the conversation thread
            checkpoint_ns: Optional namespace for organizing checkpoints
            checkpoint_id: Optional specific checkpoint ID to resume from
        
        Returns:
            Configuration dictionary for LangGraph invoke/stream
        """
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        if checkpoint_ns:
            config["configurable"]["checkpoint_ns"] = checkpoint_ns
        
        if checkpoint_id:
            config["configurable"]["checkpoint_id"] = checkpoint_id
        
        return config
    
    def list_checkpoints(
        self,
        thread_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List checkpoints for a specific thread.
        
        Args:
            thread_id: The thread ID to query
            limit: Maximum number of checkpoints to return
        
        Returns:
            List of checkpoint metadata dictionaries
        """
        if not self._checkpointer:
            with self.get_checkpointer() as checkpointer:
                return self._list_checkpoints_impl(checkpointer, thread_id, limit)
        
        return self._list_checkpoints_impl(self._checkpointer, thread_id, limit)
    
    def _list_checkpoints_impl(
        self,
        checkpointer,
        thread_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Implementation of list_checkpoints."""
        checkpoints = []
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            # Get checkpoint history
            for checkpoint_tuple in checkpointer.list(config, limit=limit):
                checkpoint, metadata = checkpoint_tuple.checkpoint, checkpoint_tuple.metadata
                checkpoints.append({
                    "checkpoint_id": checkpoint_tuple.config["configurable"].get("checkpoint_id"),
                    "thread_id": thread_id,
                    "parent_checkpoint_id": checkpoint_tuple.parent_config.get("configurable", {}).get("checkpoint_id") if checkpoint_tuple.parent_config else None,
                    "metadata": metadata,
                    "created_at": metadata.get("created_at") if metadata else None,
                })
        except Exception as e:
            print(f"Warning: Could not list checkpoints: {e}")
        
        return checkpoints
    
    def get_state(
        self,
        thread_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the state at a specific checkpoint.
        
        Args:
            thread_id: The thread ID
            checkpoint_id: Optional checkpoint ID (if None, gets latest)
        
        Returns:
            State dictionary or None if not found
        """
        config = self.create_thread_config(thread_id, checkpoint_id=checkpoint_id)
        
        if not self._checkpointer:
            with self.get_checkpointer() as checkpointer:
                return self._get_state_impl(checkpointer, config)
        
        return self._get_state_impl(self._checkpointer, config)
    
    def _get_state_impl(self, checkpointer, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Implementation of get_state."""
        try:
            checkpoint_tuple = checkpointer.get_tuple(config)
            if checkpoint_tuple:
                return checkpoint_tuple.checkpoint.get("channel_values", {})
        except Exception as e:
            print(f"Warning: Could not get state: {e}")
        
        return None
    
    def update_state(
        self,
        thread_id: str,
        state_updates: Dict[str, Any],
        checkpoint_id: Optional[str] = None
    ) -> bool:
        """
        Update the state at a specific checkpoint (creates a new checkpoint).
        
        Args:
            thread_id: The thread ID
            state_updates: Dictionary of state updates
            checkpoint_id: Optional checkpoint ID to fork from
        
        Returns:
            True if successful, False otherwise
        """
        config = self.create_thread_config(thread_id, checkpoint_id=checkpoint_id)
        
        if not self._checkpointer:
            with self.get_checkpointer() as checkpointer:
                return self._update_state_impl(checkpointer, config, state_updates)
        
        return self._update_state_impl(self._checkpointer, config, state_updates)
    
    def _update_state_impl(
        self,
        checkpointer,
        config: Dict[str, Any],
        state_updates: Dict[str, Any]
    ) -> bool:
        """Implementation of update_state."""
        try:
            # Get current checkpoint
            checkpoint_tuple = checkpointer.get_tuple(config)
            if not checkpoint_tuple:
                return False
            
            # Update state
            current_state = checkpoint_tuple.checkpoint.get("channel_values", {})
            current_state.update(state_updates)
            
            # Save updated checkpoint
            checkpoint_tuple.checkpoint["channel_values"] = current_state
            checkpointer.put(
                config,
                checkpoint_tuple.checkpoint,
                checkpoint_tuple.metadata
            )
            
            return True
        except Exception as e:
            print(f"Warning: Could not update state: {e}")
            return False


def create_checkpoint_manager_from_env() -> CheckpointManager:
    """
    Create a checkpoint manager based on environment variables.
    
    Environment Variables:
        CHECKPOINT_TYPE: Type of checkpointer (memory, sqlite, postgres)
        CHECKPOINT_DB_PATH: Path for SQLite database
        POSTGRES_CHECKPOINT_URI: PostgreSQL connection URI
    
    Returns:
        Configured CheckpointManager instance
    """
    checkpoint_type = os.getenv("CHECKPOINT_TYPE", "sqlite").lower()
    
    if checkpoint_type == "memory":
        return CheckpointManager(CheckpointerType.MEMORY)
    elif checkpoint_type == "sqlite":
        db_path = os.getenv("CHECKPOINT_DB_PATH", "./data/checkpoints.db")
        return CheckpointManager(CheckpointerType.SQLITE, db_path)
    elif checkpoint_type == "postgres":
        uri = os.getenv("POSTGRES_CHECKPOINT_URI")
        if not uri:
            raise ValueError(
                "POSTGRES_CHECKPOINT_URI environment variable required for PostgreSQL checkpointing"
            )
        return CheckpointManager(CheckpointerType.POSTGRES, uri)
    else:
        raise ValueError(f"Invalid CHECKPOINT_TYPE: {checkpoint_type}")


# Convenience functions
def get_default_checkpointer():
    """
    Get a default checkpointer (SQLite-based for development).
    
    Returns:
        SQLite checkpointer instance
    """
    manager = CheckpointManager(CheckpointerType.SQLITE)
    return manager.get_checkpointer()

