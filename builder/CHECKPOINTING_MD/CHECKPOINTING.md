# LangGraph Checkpointing - Long-Term Memory

This document explains how to use LangGraph checkpointing for long-term memory persistence in the RDBMS Builder.

## Overview

LangGraph checkpointing enables **long-term memory** by persisting the state of your graph at each step. This provides several powerful capabilities:

### Key Features

1. **Session Memory** - State persists across multiple runs using thread IDs
2. **Error Recovery** - Automatic fault tolerance and resume from last checkpoint
3. **Human-in-the-Loop** - Pause execution, get user input, and resume
4. **Time Travel** - Replay past executions and explore alternative paths
5. **Multi-Session Workflows** - Build on previous conversations over time

## Architecture

### Checkpointer Types

The RDBMS Builder supports three checkpointer backends:

| Type | Use Case | Persistence | Production Ready |
|------|----------|-------------|------------------|
| **Memory** | Testing, experimentation | ❌ No (volatile) | ❌ No |
| **SQLite** | Local development, single user | ✅ Yes (file-based) | ⚠️  Limited |
| **PostgreSQL** | Production, multi-user | ✅ Yes (database) | ✅ Yes |

### How It Works

```
User Request → Graph Execution
                    ↓
              [Checkpoint 1] - After node "plan"
                    ↓
              [Checkpoint 2] - After node "clarify"
                    ↓
              [Checkpoint 3] - After node "extract_entities"
                    ↓
                  ... (continues for each node)
                    ↓
              [Checkpoint N] - Final state
```

Each checkpoint contains:
- Complete graph state (working + archive)
- Node execution results
- Metadata (timestamp, parent checkpoint, etc.)
- Thread ID for session tracking

## Installation

### Dependencies

Add checkpointing dependencies to your environment:

```bash
# For SQLite checkpointing (recommended for development)
pip install langgraph-checkpoint-sqlite

# For PostgreSQL checkpointing (recommended for production)
pip install langgraph-checkpoint-postgres psycopg

# Or install from requirements
pip install -e .
```

### Environment Variables

Configure checkpointing via environment variables:

```bash
# Checkpoint type: memory, sqlite, or postgres
export CHECKPOINT_TYPE=sqlite

# SQLite database path (for sqlite type)
export CHECKPOINT_DB_PATH=./data/checkpoints.db

# PostgreSQL connection URI (for postgres type)
export POSTGRES_CHECKPOINT_URI=postgresql://user:password@localhost:5432/rdbms_builder
```

## Usage

### Basic Usage

```python
from main import run_builder
from utils.checkpoint_manager import CheckpointerType

# Run with checkpointing enabled
result = run_builder(
    requirements="Build a blog system...",
    dialect="postgresql",
    enable_checkpointing=True,
    checkpoint_type=CheckpointerType.SQLITE,
    checkpoint_connection="./data/checkpoints.db"
)
```

### Resume from Checkpoint

```python
from main import resume_from_checkpoint
from utils.checkpoint_manager import CheckpointerType

# Resume from a previous thread
thread_id = "abc123..."  # Your thread ID

state = resume_from_checkpoint(
    thread_id=thread_id,
    checkpoint_type=CheckpointerType.SQLITE,
    connection_string="./data/checkpoints.db"
)

# Continue execution with the resumed state
if state:
    result = run_builder(
        requirements="Additional requirements...",
        thread_id=thread_id,  # Use same thread ID
        enable_checkpointing=True,
        checkpoint_type=CheckpointerType.SQLITE
    )
```

### List Checkpoint History

```python
from main import list_checkpoints
from utils.checkpoint_manager import CheckpointerType

# View all checkpoints for a thread
list_checkpoints(
    thread_id="abc123...",
    checkpoint_type=CheckpointerType.SQLITE,
    connection_string="./data/checkpoints.db",
    limit=10
)
```

### Using CheckpointManager Directly

```python
from utils.checkpoint_manager import CheckpointManager, CheckpointerType
from graph.builder import get_compiled_graphs

# Initialize checkpoint manager
checkpoint_manager = CheckpointManager(
    checkpointer_type=CheckpointerType.SQLITE,
    connection_string="./data/checkpoints.db"
)

# Use context manager for proper lifecycle
with checkpoint_manager.get_checkpointer() as checkpointer:
    # Get compiled graphs with checkpointing
    graph, graph_continue = get_compiled_graphs(checkpointer)
    
    # Create thread config
    config = CheckpointManager.create_thread_config(thread_id)
    
    # Execute with checkpointing
    result = graph.invoke(state, config=config)

# Checkpointer automatically cleaned up
```

## Use Cases

### 1. Multi-Session Conversations

Build complex schemas over multiple sessions:

```python
# Session 1: Initial schema
result1 = run_builder(
    requirements="Build an e-commerce system with products and orders",
    thread_id="my-ecommerce-project",
    enable_checkpointing=True
)

# ... Later that day or week ...

# Session 2: Extend the schema (same thread)
result2 = run_builder(
    requirements="Add product reviews and ratings",
    thread_id="my-ecommerce-project",  # Same thread ID!
    enable_checkpointing=True
)

# The graph remembers the previous schema and builds upon it
```

### 2. Error Recovery

Automatic recovery from failures:

```python
try:
    result = run_builder(
        requirements="Complex schema...",
        thread_id="my-project",
        enable_checkpointing=True
    )
except Exception as e:
    print(f"Error: {e}")
    
    # Resume from last successful checkpoint
    state = resume_from_checkpoint(thread_id="my-project")
    
    # Continue from where it left off
    result = run_builder(
        requirements="Continue...",
        thread_id="my-project",
        enable_checkpointing=True
    )
```

### 3. Human-in-the-Loop

Interactive schema refinement:

```python
# Run initial generation
result = run_builder(
    requirements="Initial requirements...",
    thread_id="interactive-project",
    enable_checkpointing=True,
    enable_critic=True  # Get feedback
)

# Review generated schema
print(result["archive"]["ddl_script"])

# User decides to refine
state = resume_from_checkpoint(thread_id="interactive-project")

# Apply manual modifications to state
state["working"]["tables"].append({...})  # Add custom table

# Continue with modified state
result = run_builder(
    requirements="Continue with modifications...",
    thread_id="interactive-project",
    enable_checkpointing=True
)
```

### 4. Time Travel Debugging

Inspect and replay past states:

```python
# List all checkpoints
checkpoints = checkpoint_manager.list_checkpoints("my-thread")

# Get state at specific checkpoint
state_at_checkpoint = checkpoint_manager.get_state(
    thread_id="my-thread",
    checkpoint_id=checkpoints[3]["checkpoint_id"]
)

# Analyze what happened at that point
print(state_at_checkpoint["working"]["entities"])
print(state_at_checkpoint["working"]["tables"])

# Fork from that checkpoint to try different approach
result = run_builder(
    requirements="Alternative approach...",
    thread_id="my-thread-fork",
    enable_checkpointing=True
)
```

## Configuration

### SQLite Configuration

Recommended for:
- Local development
- Single-user applications
- File-based persistence

```python
from utils.checkpoint_manager import CheckpointManager, CheckpointerType

manager = CheckpointManager(
    checkpointer_type=CheckpointerType.SQLITE,
    connection_string="./data/checkpoints.db"
)
```

File structure:
```
./data/
  └── checkpoints.db  # SQLite database with checkpoint tables
```

### PostgreSQL Configuration

Recommended for:
- Production environments
- Multi-user applications
- Distributed systems

```python
from utils.checkpoint_manager import CheckpointManager, CheckpointerType

manager = CheckpointManager(
    checkpointer_type=CheckpointerType.POSTGRES,
    connection_string="postgresql://user:password@localhost:5432/rdbms_builder"
)
```

Connection string format:
```
postgresql://[user[:password]@][host][:port][/dbname]
```

### Memory Configuration (Testing Only)

Recommended for:
- Unit tests
- Quick experiments
- No persistence needed

```python
from utils.checkpoint_manager import CheckpointManager, CheckpointerType

manager = CheckpointManager(
    checkpointer_type=CheckpointerType.MEMORY
)
```

⚠️ **Warning**: All data is lost when the process terminates.

## Best Practices

### 1. Thread ID Management

- Use **descriptive thread IDs** for multi-session projects
- Use **UUIDs** for one-off generations
- **Don't reuse** thread IDs across different projects

```python
# Good: Descriptive thread IDs
thread_id = "project-ecommerce-v2"
thread_id = "client-acme-inventory-system"

# Good: UUIDs for single sessions
thread_id = str(uuid.uuid4())

# Bad: Generic thread IDs for different projects
thread_id = "my-project"  # Too vague
```

### 2. Checkpoint Storage

- **SQLite**: Store in `./data/` directory (gitignored)
- **PostgreSQL**: Use dedicated database or schema
- **Cleanup**: Implement retention policies for old checkpoints

```python
# Example: Delete old checkpoints
def cleanup_old_checkpoints(days=30):
    # Implementation depends on checkpointer type
    # Delete checkpoints older than N days
    pass
```

### 3. Error Handling

Always handle checkpointing errors gracefully:

```python
try:
    result = run_builder(
        requirements="...",
        enable_checkpointing=True
    )
except ImportError as e:
    print(f"Checkpointing disabled: {e}")
    # Fall back to non-checkpointed execution
    result = run_builder(
        requirements="...",
        enable_checkpointing=False
    )
```

### 4. Performance Considerations

- Checkpointing adds **minimal overhead** (~10-50ms per checkpoint)
- **SQLite** is fast for single-user scenarios
- **PostgreSQL** scales better for concurrent users
- Consider **checkpoint frequency** for very large states

## API Reference

### CheckpointManager

Main class for managing checkpoints.

```python
class CheckpointManager:
    def __init__(
        self,
        checkpointer_type: CheckpointerType,
        connection_string: Optional[str] = None,
        **kwargs
    )
    
    def get_checkpointer(self) -> ContextManager
    def list_checkpoints(self, thread_id: str, limit: int = 10) -> List[Dict]
    def get_state(self, thread_id: str, checkpoint_id: Optional[str] = None) -> Optional[Dict]
    def update_state(self, thread_id: str, state_updates: Dict) -> bool
    
    @staticmethod
    def create_thread_config(
        thread_id: str,
        checkpoint_ns: Optional[str] = None,
        checkpoint_id: Optional[str] = None
    ) -> Dict
```

### Main Functions

```python
def run_builder(
    requirements: str,
    enable_checkpointing: bool = True,
    checkpoint_type: CheckpointerType = CheckpointerType.SQLITE,
    checkpoint_connection: Optional[str] = None,
    thread_id: Optional[str] = None,
    ...
) -> GraphState

def resume_from_checkpoint(
    thread_id: str,
    checkpoint_id: Optional[str] = None,
    checkpoint_type: CheckpointerType = CheckpointerType.SQLITE,
    connection_string: Optional[str] = None,
) -> Optional[GraphState]

def list_checkpoints(
    thread_id: str,
    checkpoint_type: CheckpointerType = CheckpointerType.SQLITE,
    connection_string: Optional[str] = None,
    limit: int = 10
) -> None
```

## Troubleshooting

### Import Errors

**Problem**: `ImportError: SQLite checkpointer not available`

**Solution**:
```bash
pip install langgraph-checkpoint-sqlite
```

### Connection Errors

**Problem**: `Error connecting to PostgreSQL`

**Solution**:
- Check connection string format
- Verify database exists
- Check network/firewall settings
- Ensure PostgreSQL is running

### State Not Found

**Problem**: `No state found at checkpoint`

**Solution**:
- Verify thread_id is correct
- Check checkpoint_id exists
- Ensure checkpointer type matches
- Verify database file/connection

### Performance Issues

**Problem**: Slow checkpoint operations

**Solution**:
- For SQLite: Ensure disk I/O is not bottleneck
- For PostgreSQL: Check database indexes
- Consider reducing state size
- Implement checkpoint pruning

## Examples

See the complete working examples in:
- `examples/checkpointing_demo.py` - Interactive demos
- `main.py` - Production usage patterns

Run the demo:
```bash
python examples/checkpointing_demo.py
```

## Additional Resources

- [LangGraph Checkpointing Documentation](https://python.langchain.com/docs/langgraph/checkpointing)
- [LangGraph Persistence Guide](https://python.langchain.com/docs/langgraph/persistence)
- [SQLite Checkpointer](https://python.langchain.com/docs/langgraph/checkpointing#sqlite)
- [PostgreSQL Checkpointer](https://python.langchain.com/docs/langgraph/checkpointing#postgresql)

## Migration Guide

### From State-Only to Checkpointing

If you're currently using state-only (short-term memory):

**Before:**
```python
result = run_builder(requirements="...")
# State is lost after execution
```

**After:**
```python
result = run_builder(
    requirements="...",
    thread_id="my-project",
    enable_checkpointing=True
)
# State is preserved across sessions
```

No other code changes required! The system is backward compatible.

