# Checkpoint Database Inspection Guide

This guide shows you how to configure, access, and inspect the checkpoint database to see what's being saved.

## Quick Start

### SQLite (Recommended for Development)

The easiest way to get started:

```bash
# Run the system with default SQLite checkpointing
python main.py
# Choose: Enable checkpointing? [Y/n]: Y
# Choose: Checkpoint type [1=SQLite]: 1
# Database will be created at: ./data/checkpoints.db
```

### View the Database

Once you have checkpoints, use any of these tools:

#### Option 1: SQLite Browser (GUI - Recommended)
```bash
# Install DB Browser for SQLite
# macOS:
brew install --cask db-browser-for-sqlite

# Or download from: https://sqlitebrowser.org/

# Open the database
open -a "DB Browser for SQLite" ./data/checkpoints.db
```

#### Option 2: SQLite Command Line
```bash
# Open database in terminal
sqlite3 ./data/checkpoints.db

# List all tables
.tables

# View schema
.schema

# Query checkpoints
SELECT * FROM checkpoints LIMIT 5;

# Exit
.quit
```

#### Option 3: Python Script (Custom Viewer)
```bash
# Use the provided inspection script
python scripts/inspect_checkpoints.py
```

## Database Schema

### SQLite Tables

LangGraph creates these tables automatically:

```sql
-- Main checkpoint storage
CREATE TABLE checkpoints (
    thread_id TEXT,
    checkpoint_ns TEXT,
    checkpoint_id TEXT,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint BLOB,  -- Serialized state
    metadata TEXT,    -- JSON metadata
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- Write operations log
CREATE TABLE checkpoint_writes (
    thread_id TEXT,
    checkpoint_ns TEXT,
    checkpoint_id TEXT,
    task_id TEXT,
    idx INTEGER,
    channel TEXT,
    type TEXT,
    value BLOB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

### Key Fields

- **thread_id**: Your conversation/project thread identifier
- **checkpoint_id**: Unique ID for each checkpoint
- **parent_checkpoint_id**: Previous checkpoint (for history)
- **checkpoint**: Binary data containing your GraphState
- **metadata**: JSON with timestamps, tags, etc.

## Inspection Methods

### Method 1: Using Python Inspection Script

```python
# scripts/inspect_checkpoints.py
from utils.checkpoint_manager import CheckpointManager, CheckpointerType
import json
import pickle

def inspect_database(db_path="./data/checkpoints.db"):
    """Inspect all checkpoints in the database."""
    manager = CheckpointManager(
        checkpointer_type=CheckpointerType.SQLITE,
        connection_string=db_path
    )
    
    print(f"\n{'='*70}")
    print(f"📊 Checkpoint Database: {db_path}")
    print(f"{'='*70}\n")
    
    # Get all threads
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List all unique threads
    cursor.execute("SELECT DISTINCT thread_id FROM checkpoints")
    threads = cursor.fetchall()
    
    print(f"Total Threads: {len(threads)}\n")
    
    for thread_id, in threads:
        print(f"🧵 Thread: {thread_id[:16]}...")
        
        # Get checkpoints for this thread
        checkpoints = manager.list_checkpoints(thread_id, limit=100)
        print(f"   Checkpoints: {len(checkpoints)}")
        
        # Get latest state
        state = manager.get_state(thread_id)
        if state:
            working = state.get("working", {})
            archive = state.get("archive", {})
            
            print(f"   Entities: {len(working.get('entities', []))}")
            print(f"   Tables: {len(working.get('tables', []))}")
            print(f"   LLM Calls: {archive.get('total_llm_calls', 0)}")
            print(f"   Has DDL: {'✓' if archive.get('ddl_script') else '✗'}")
        print()
    
    conn.close()

if __name__ == "__main__":
    inspect_database()
```

### Method 2: Interactive Checkpoint Viewer

```python
# scripts/checkpoint_viewer.py
from utils.checkpoint_manager import CheckpointManager, CheckpointerType
import json

def interactive_viewer():
    """Interactive checkpoint viewer."""
    db_path = input("Database path [./data/checkpoints.db]: ").strip()
    if not db_path:
        db_path = "./data/checkpoints.db"
    
    manager = CheckpointManager(
        checkpointer_type=CheckpointerType.SQLITE,
        connection_string=db_path
    )
    
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    while True:
        print("\n" + "="*50)
        print("Checkpoint Viewer")
        print("="*50)
        print("1. List all threads")
        print("2. View thread checkpoints")
        print("3. View checkpoint state")
        print("4. Export state to JSON")
        print("5. Exit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == "1":
            cursor.execute("SELECT DISTINCT thread_id FROM checkpoints")
            threads = cursor.fetchall()
            print(f"\nFound {len(threads)} threads:")
            for i, (tid,) in enumerate(threads, 1):
                print(f"{i}. {tid}")
        
        elif choice == "2":
            thread_id = input("Thread ID: ").strip()
            checkpoints = manager.list_checkpoints(thread_id, limit=50)
            print(f"\nFound {len(checkpoints)} checkpoints:")
            for cp in checkpoints:
                print(f"  ID: {cp.get('checkpoint_id', 'N/A')[:16]}...")
                print(f"  Created: {cp.get('created_at', 'N/A')}")
                print()
        
        elif choice == "3":
            thread_id = input("Thread ID: ").strip()
            state = manager.get_state(thread_id)
            if state:
                print(json.dumps(state, indent=2, default=str))
            else:
                print("No state found")
        
        elif choice == "4":
            thread_id = input("Thread ID: ").strip()
            output_file = input("Output file [state.json]: ").strip() or "state.json"
            state = manager.get_state(thread_id)
            if state:
                with open(output_file, 'w') as f:
                    json.dump(state, f, indent=2, default=str)
                print(f"✓ Exported to {output_file}")
            else:
                print("No state found")
        
        elif choice == "5":
            break
    
    conn.close()

if __name__ == "__main__":
    interactive_viewer()
```

### Method 3: SQL Queries

```sql
-- Connect to database
sqlite3 ./data/checkpoints.db

-- Show all threads
SELECT DISTINCT thread_id FROM checkpoints;

-- Count checkpoints per thread
SELECT thread_id, COUNT(*) as checkpoint_count 
FROM checkpoints 
GROUP BY thread_id;

-- Show recent checkpoints
SELECT 
    thread_id,
    checkpoint_id,
    parent_checkpoint_id,
    metadata
FROM checkpoints
ORDER BY rowid DESC
LIMIT 10;

-- Show checkpoint metadata
SELECT 
    thread_id,
    json_extract(metadata, '$.created_at') as created_at,
    json_extract(metadata, '$.step') as step
FROM checkpoints
LIMIT 10;

-- Find specific thread
SELECT * FROM checkpoints 
WHERE thread_id LIKE 'abc123%'
LIMIT 5;
```

## PostgreSQL Setup

### Configure PostgreSQL

```bash
# Create database
createdb rdbms_builder

# Or using psql
psql -U postgres
CREATE DATABASE rdbms_builder;
\q

# Set environment variable
export POSTGRES_CHECKPOINT_URI="postgresql://localhost:5432/rdbms_builder"

# Run with PostgreSQL checkpointing
python main.py
# Choose: Checkpoint type [2=PostgreSQL]: 2
```

### View PostgreSQL Database

```bash
# Connect to database
psql -U postgres rdbms_builder

# List tables
\dt

# View schema
\d checkpoints

# Query checkpoints
SELECT thread_id, checkpoint_id, metadata 
FROM checkpoints 
LIMIT 5;

# Count checkpoints
SELECT COUNT(*) FROM checkpoints;

# Exit
\q
```

### PostgreSQL Queries

```sql
-- Show all threads with checkpoint counts
SELECT 
    thread_id,
    COUNT(*) as checkpoints,
    MAX(metadata::json->>'created_at') as last_checkpoint
FROM checkpoints
GROUP BY thread_id
ORDER BY last_checkpoint DESC;

-- Show checkpoint chain for a thread
SELECT 
    checkpoint_id,
    parent_checkpoint_id,
    metadata::json->>'created_at' as created_at
FROM checkpoints
WHERE thread_id = 'your-thread-id'
ORDER BY created_at;
```

## Understanding the Saved Data

### What's in a Checkpoint?

Each checkpoint contains the **complete GraphState**:

```python
checkpoint = {
    "working": {
        "user_requirements": "...",
        "sql_dialect": "postgresql",
        "current_step": "design_schema",
        "entities": [...],
        "relationships": [...],
        "tables": [...],
        # ... all working state
    },
    "archive": {
        "tasks": [...],
        "critic_reports": [...],
        "ddl_script": "CREATE TABLE ...",
        "erd_diagram": "graph TD ...",
        "nestjs_architecture": {...},
        # ... all archive state
    }
}
```

### Checkpoint Metadata

```json
{
  "created_at": "2025-12-12T10:30:45.123Z",
  "step": "design_schema",
  "source": "update",
  "writes": {
    "design_schema": {
      "working": {...}
    }
  }
}
```

## Practical Examples

### Example 1: Find Your Latest Project

```bash
# Connect to database
sqlite3 ./data/checkpoints.db

# Find your thread
SELECT thread_id, metadata 
FROM checkpoints 
WHERE json_extract(metadata, '$.created_at') > datetime('now', '-1 day')
ORDER BY rowid DESC;
```

### Example 2: Export Schema from Checkpoint

```python
from utils.checkpoint_manager import CheckpointManager, CheckpointerType

manager = CheckpointManager(
    checkpointer_type=CheckpointerType.SQLITE,
    connection_string="./data/checkpoints.db"
)

# Get state
state = manager.get_state("your-thread-id")

# Extract DDL
ddl = state["archive"]["ddl_script"]
print(ddl)

# Save to file
with open("exported_schema.sql", "w") as f:
    f.write(ddl)
```

### Example 3: Compare Checkpoints

```python
# Get two checkpoints
state1 = manager.get_state("thread-id", checkpoint_id="cp1")
state2 = manager.get_state("thread-id", checkpoint_id="cp2")

# Compare tables
tables1 = {t["name"] for t in state1["working"]["tables"]}
tables2 = {t["name"] for t in state2["working"]["tables"]}

print(f"New tables: {tables2 - tables1}")
print(f"Removed tables: {tables1 - tables2}")
```

## Cleanup and Maintenance

### Remove Old Checkpoints

```python
import sqlite3
from datetime import datetime, timedelta

def cleanup_old_checkpoints(db_path, days=30):
    """Remove checkpoints older than N days."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    cursor.execute("""
        DELETE FROM checkpoints 
        WHERE json_extract(metadata, '$.created_at') < ?
    """, (cutoff,))
    
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"Deleted {deleted} old checkpoints")

# Usage
cleanup_old_checkpoints("./data/checkpoints.db", days=30)
```

### Vacuum Database

```bash
# Compact SQLite database after deletions
sqlite3 ./data/checkpoints.db "VACUUM;"
```

## Troubleshooting

### Database Locked

If you get "database is locked" errors:

```bash
# Close all connections
# Check for processes using the database
lsof ./data/checkpoints.db

# Kill if necessary
kill -9 <PID>
```

### Large Database Size

```bash
# Check size
du -h ./data/checkpoints.db

# Analyze growth
sqlite3 ./data/checkpoints.db "SELECT COUNT(*) FROM checkpoints;"

# Clean up old data (see cleanup section above)
```

### Corrupted Database

```bash
# Check integrity
sqlite3 ./data/checkpoints.db "PRAGMA integrity_check;"

# Recover if possible
sqlite3 ./data/checkpoints.db ".dump" | sqlite3 new_checkpoints.db
```

## GUI Tools

### Recommended Tools

1. **DB Browser for SQLite** (Best for SQLite)
   - Download: https://sqlitebrowser.org/
   - Free, open-source
   - Visual query builder
   - Schema viewer
   - Data editor

2. **DBeaver** (Works with both SQLite and PostgreSQL)
   - Download: https://dbeaver.io/
   - Universal database tool
   - ER diagrams
   - Query builder

3. **pgAdmin** (For PostgreSQL)
   - Download: https://www.pgadmin.org/
   - Official PostgreSQL GUI
   - Full management features

4. **TablePlus** (Commercial, very polished)
   - Download: https://tableplus.com/
   - Works with both SQLite and PostgreSQL
   - Modern UI

## Next Steps

1. Install a database viewer (DB Browser recommended)
2. Run a workflow with checkpointing enabled
3. Open `./data/checkpoints.db` in the viewer
4. Explore the tables and data structure
5. Try the Python inspection scripts

Happy exploring! 🔍

