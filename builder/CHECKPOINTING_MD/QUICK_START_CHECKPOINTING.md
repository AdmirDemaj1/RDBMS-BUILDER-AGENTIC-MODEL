# Quick Start: Viewing Your Checkpoints

A simple guide to view and inspect your saved checkpoint data.

## 1. Run with Checkpointing

```bash
python main.py
```

When prompted:
- **Enable checkpointing?** → Press `Y`
- **Checkpoint type** → Press `1` (SQLite)
- Database will be created at: `./data/checkpoints.db`

## 2. View Your Data (Choose One Method)

### Method A: Quick Inspection (Recommended First)

```bash
python scripts/inspect_checkpoints.py
```

This shows you:
- All threads in your database
- Number of checkpoints per thread
- Latest state summary
- Entity/table counts
- LLM usage stats

### Method B: Interactive Viewer (Most Features)

```bash
python scripts/checkpoint_viewer.py
```

Features:
- Browse all threads
- View checkpoint history
- Explore state details
- Export to JSON
- Export DDL scripts

### Method C: GUI Tool (Best for Exploration)

**Install DB Browser for SQLite:**

```bash
# macOS
brew install --cask db-browser-for-sqlite

# Or download from: https://sqlitebrowser.org/
```

**Open your database:**

```bash
open -a "DB Browser for SQLite" ./data/checkpoints.db
```

Then explore:
1. Click "Browse Data" tab
2. Select "checkpoints" table
3. View your saved states

### Method D: Command Line (SQL Queries)

```bash
sqlite3 ./data/checkpoints.db
```

Try these queries:

```sql
-- Show all threads
SELECT DISTINCT thread_id FROM checkpoints;

-- Count checkpoints
SELECT COUNT(*) FROM checkpoints;

-- Show recent activity
SELECT 
    thread_id,
    json_extract(metadata, '$.created_at') as created
FROM checkpoints
ORDER BY created DESC
LIMIT 10;

-- Exit
.quit
```

## 3. Export Your Data

### Export Specific Thread

```bash
# List threads first
python scripts/inspect_checkpoints.py

# Export a thread's state
python scripts/inspect_checkpoints.py --export YOUR_THREAD_ID

# Specify output file
python scripts/inspect_checkpoints.py --export YOUR_THREAD_ID --output my_state.json
```

### Export DDL Script

Using the interactive viewer:

```bash
python scripts/checkpoint_viewer.py
# Then: Option 2 → Select thread → Option 6 → Export DDL
```

Or programmatically:

```python
from utils.checkpoint_manager import CheckpointManager, CheckpointerType

manager = CheckpointManager(
    checkpointer_type=CheckpointerType.SQLITE,
    connection_string="./data/checkpoints.db"
)

state = manager.get_state("your-thread-id")
ddl = state["archive"]["ddl_script"]

with open("schema.sql", "w") as f:
    f.write(ddl)
```

## 4. Understanding the Data

### What's Saved?

Each checkpoint contains:

```
Checkpoint
├── working (in-memory state)
│   ├── entities: [...]
│   ├── tables: [...]
│   ├── current_step: "..."
│   └── ... (all working data)
└── archive (historical data)
    ├── ddl_script: "CREATE TABLE ..."
    ├── erd_diagram: "graph TD ..."
    ├── nestjs_architecture: {...}
    └── ... (all generated outputs)
```

### Thread IDs

- Each execution has a unique `thread_id`
- Same thread ID = resume previous session
- Different thread ID = new independent session

## 5. Common Tasks

### Find My Latest Project

```bash
python scripts/inspect_checkpoints.py
# Look at the top result (sorted by most recent)
```

### Resume Previous Session

```python
from main import run_builder

# Use the same thread_id from previous run
result = run_builder(
    requirements="Continue where I left off...",
    thread_id="your-previous-thread-id",
    enable_checkpointing=True
)
```

### Compare Two Versions

```python
from utils.checkpoint_manager import CheckpointManager, CheckpointerType

manager = CheckpointManager(
    checkpointer_type=CheckpointerType.SQLITE,
    connection_string="./data/checkpoints.db"
)

# Get states
state1 = manager.get_state("thread-1")
state2 = manager.get_state("thread-2")

# Compare
tables1 = [t["name"] for t in state1["working"]["tables"]]
tables2 = [t["name"] for t in state2["working"]["tables"]]

print(f"Thread 1 tables: {tables1}")
print(f"Thread 2 tables: {tables2}")
```

## 6. Cleanup

### Remove Old Checkpoints

```bash
# Delete specific thread
sqlite3 ./data/checkpoints.db "DELETE FROM checkpoints WHERE thread_id = 'old-thread-id';"

# Compact database
sqlite3 ./data/checkpoints.db "VACUUM;"
```

### Delete Everything (Fresh Start)

```bash
rm ./data/checkpoints.db
# Database will be recreated on next run
```

## Troubleshooting

### "Database not found"

You need to run the system with checkpointing enabled first:

```bash
python main.py
# Choose: Enable checkpointing? Y
```

### "Cannot import CheckpointManager"

Install dependencies:

```bash
pip install -e .
```

Or manually:

```bash
pip install langgraph-checkpoint-sqlite
```

### Database Locked

Close all programs/scripts accessing the database, then try again.

## Next Steps

- 📖 Read [DATABASE_INSPECTION.md](DATABASE_INSPECTION.md) for advanced usage
- 📖 Read [CHECKPOINTING.md](CHECKPOINTING.md) for complete documentation
- 🎮 Try [examples/checkpointing_demo.py](examples/checkpointing_demo.py) for demos

## Quick Reference

| Task | Command |
|------|---------|
| View all checkpoints | `python scripts/inspect_checkpoints.py` |
| Interactive browser | `python scripts/checkpoint_viewer.py` |
| Open in GUI | `open -a "DB Browser for SQLite" ./data/checkpoints.db` |
| SQL queries | `sqlite3 ./data/checkpoints.db` |
| Export thread | `python scripts/inspect_checkpoints.py --export THREAD_ID` |
| Delete database | `rm ./data/checkpoints.db` |

---

**Need Help?** Check the documentation files:
- `DATABASE_INSPECTION.md` - Detailed inspection guide
- `CHECKPOINTING.md` - Complete checkpointing documentation

