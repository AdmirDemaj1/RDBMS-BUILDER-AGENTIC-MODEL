"""
Long-Term Memory Manager for Parent Graph
Handles hierarchical checkpointing: Parent → Subgraphs
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
try:
    from langgraph.checkpoint.postgres import PostgresSaver
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class MemoryScope(str, Enum):
    """Memory scope for different graph levels"""
    PARENT = "parent"
    BUILDER = "builder"
    ENHANCER = "enhancer"


class LongTermMemoryManager:
    """
    Manages long-term memory across parent and subgraph conversations.
    """
    
    def __init__(
        self,
        checkpointer_type: str = "sqlite",
        db_path: Optional[str] = None,
        postgres_uri: Optional[str] = None
    ):
        """Initialize memory manager"""
        self.checkpointer_type = checkpointer_type
        self.db_path = db_path or "./data/parent_graph_memory.db"
        self.postgres_uri = postgres_uri
        
        self._parent_checkpointer = None
        self._builder_checkpointer = None
        self._enhancer_checkpointer = None
        
        # Store context managers for cleanup
        self._context_managers = []
        
        self._initialize_checkpointers()
    
    def _initialize_checkpointers(self):
        """Initialize checkpointers for each scope"""
        if self.checkpointer_type == "memory":
            self._parent_checkpointer = MemorySaver()
            self._builder_checkpointer = MemorySaver()
            self._enhancer_checkpointer = MemorySaver()
            
        elif self.checkpointer_type == "sqlite":
            import sqlite3
            import os
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
            
            # Create connections and SqliteSaver instances
            # SqliteSaver.from_conn_string returns a context manager, so we need to enter it
            parent_ctx = SqliteSaver.from_conn_string(self.db_path)
            builder_ctx = SqliteSaver.from_conn_string(self.db_path)
            enhancer_ctx = SqliteSaver.from_conn_string(self.db_path)
            
            # Enter context managers to get actual checkpointers
            self._parent_checkpointer = parent_ctx.__enter__()
            self._builder_checkpointer = builder_ctx.__enter__()
            self._enhancer_checkpointer = enhancer_ctx.__enter__()
            
            # Store for cleanup
            self._context_managers = [parent_ctx, builder_ctx, enhancer_ctx]
            
        elif self.checkpointer_type == "postgres":
            if not POSTGRES_AVAILABLE:
                raise ImportError("PostgresSaver not available")
            
            parent_ctx = PostgresSaver.from_conn_string(self.postgres_uri)
            builder_ctx = PostgresSaver.from_conn_string(self.postgres_uri)
            enhancer_ctx = PostgresSaver.from_conn_string(self.postgres_uri)
            
            self._parent_checkpointer = parent_ctx.__enter__()
            self._builder_checkpointer = builder_ctx.__enter__()
            self._enhancer_checkpointer = enhancer_ctx.__enter__()
            
            self._context_managers = [parent_ctx, builder_ctx, enhancer_ctx]
        
        else:
            raise ValueError(f"Unknown checkpointer type: {self.checkpointer_type}")
    
    def get_checkpointer(self, scope: MemoryScope) -> BaseCheckpointSaver:
        """Get checkpointer for a specific scope"""
        if scope == MemoryScope.PARENT:
            return self._parent_checkpointer
        elif scope == MemoryScope.BUILDER:
            return self._builder_checkpointer
        elif scope == MemoryScope.ENHANCER:
            return self._enhancer_checkpointer
        else:
            raise ValueError(f"Unknown scope: {scope}")
    
    @staticmethod
    def create_thread_config(thread_id: str, scope: MemoryScope) -> dict:
        """Create thread configuration for checkpointing"""
        return {
            "configurable": {
                "thread_id": thread_id,
                "scope": scope.value,
                "checkpoint_ns": scope.value
            }
        }
    
    def get_conversation_state(
        self,
        thread_id: str,
        scope: MemoryScope,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve conversation state at a specific checkpoint"""
        checkpointer = self.get_checkpointer(scope)
        config = self.create_thread_config(thread_id, scope)
        
        try:
            if checkpoint_id:
                config["configurable"]["checkpoint_id"] = checkpoint_id
            
            checkpoint_tuple = checkpointer.get_tuple(config)
            
            if checkpoint_tuple and checkpoint_tuple.checkpoint:
                return checkpoint_tuple.checkpoint.get("channel_values")
            
            return None
            
        except Exception as e:
            print(f"⚠️  Error retrieving state: {e}")
            return None
    
    def list_conversations(
        self,
        scope: Optional[MemoryScope] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List previous conversations"""
        if self.checkpointer_type == "memory":
            print("⚠️  Memory checkpointer doesn't support listing")
            return []
        
        if self.checkpointer_type == "sqlite":
            return self._list_sqlite_conversations(scope, limit)
        
        return []
    
    def _list_sqlite_conversations(
        self,
        scope: Optional[MemoryScope],
        limit: int
    ) -> List[Dict[str, Any]]:
        """List conversations from SQLite"""
        import sqlite3
        import os
        
        if not os.path.exists(self.db_path):
            return []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if scope:
                query = """
                    SELECT DISTINCT thread_id, COUNT(*) as checkpoint_count
                    FROM checkpoints
                    WHERE json_extract(metadata, '$.scope') = ?
                    GROUP BY thread_id
                    ORDER BY MAX(rowid) DESC
                    LIMIT ?
                """
                cursor.execute(query, (scope.value, limit))
            else:
                query = """
                    SELECT DISTINCT thread_id, COUNT(*) as checkpoint_count
                    FROM checkpoints
                    GROUP BY thread_id
                    ORDER BY MAX(rowid) DESC
                    LIMIT ?
                """
                cursor.execute(query, (limit,))
            
            conversations = []
            for row in cursor.fetchall():
                conversations.append({
                    "thread_id": row[0],
                    "checkpoint_count": row[1],
                    "scope": scope.value if scope else "all"
                })
            
            conn.close()
            return conversations
            
        except Exception as e:
            print(f"⚠️  Error listing conversations: {e}")
            return []
    
    def cleanup(self):
        """Cleanup resources - exit context managers"""
        for ctx in self._context_managers:
            try:
                ctx.__exit__(None, None, None)
            except Exception as e:
                print(f"⚠️  Error during cleanup: {e}")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_memory_manager(
    checkpointer_type: str = "sqlite",
    db_path: Optional[str] = None,
    postgres_uri: Optional[str] = None
) -> LongTermMemoryManager:
    """Factory function to create memory manager"""
    return LongTermMemoryManager(
        checkpointer_type=checkpointer_type,
        db_path=db_path,
        postgres_uri=postgres_uri
    )


def resume_conversation(
    memory_manager: LongTermMemoryManager,
    thread_id: str,
    scope: MemoryScope = MemoryScope.PARENT
) -> Optional[Dict[str, Any]]:
    """Resume a conversation from a previous session"""
    print(f"\n🔄 Resuming {scope.value} conversation...")
    print(f"   Thread: {thread_id[:8]}...")
    
    state = memory_manager.get_conversation_state(thread_id, scope)
    
    if state:
        print(f"   ✅ State retrieved successfully")
        
        if scope == MemoryScope.PARENT:
            working = state.get("working", {})
            print(f"   Mode: {working.get('mode', 'N/A')}")
            print(f"   Iteration: {working.get('iteration_count', 0)}")
        
        return state
    else:
        print(f"   ❌ No previous state found")
        return None


def list_and_select_conversation(
    memory_manager: LongTermMemoryManager,
    scope: MemoryScope = MemoryScope.PARENT,
    limit: int = 10
) -> Optional[str]:
    """Interactive conversation selection"""
    conversations = memory_manager.list_conversations(scope, limit)
    
    if not conversations:
        print(f"\n📝 No previous {scope.value} conversations found.")
        return None
    
    print(f"\n" + "=" * 60)
    print(f"📚 PREVIOUS {scope.value.upper()} CONVERSATIONS")
    print("=" * 60)
    
    for i, conv in enumerate(conversations, 1):
        print(f"\n{i}. Thread: {conv['thread_id'][:16]}...")
        print(f"   Checkpoints: {conv['checkpoint_count']}")
    
    print("\n" + "=" * 60)
    
    choice = input("\nSelect conversation number (or Enter for new): ").strip()
    
    if not choice:
        return None
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(conversations):
            return conversations[idx]["thread_id"]
        else:
            print("❌ Invalid selection")
            return None
    except ValueError:
        print("❌ Invalid input")
        return None