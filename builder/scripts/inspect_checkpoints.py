#!/usr/bin/env python3
"""
Checkpoint Database Inspector

This script helps you inspect and view checkpoint data saved by LangGraph.
"""

import sys
import os
import json
import sqlite3
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import directly from checkpoint_manager module to avoid circular imports
import importlib.util
checkpoint_manager_path = os.path.join(
    os.path.dirname(__file__), '..', 'utils', 'checkpoint_manager.py'
)
spec = importlib.util.spec_from_file_location("checkpoint_manager", checkpoint_manager_path)
checkpoint_manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkpoint_manager)

CheckpointManager = checkpoint_manager.CheckpointManager
CheckpointerType = checkpoint_manager.CheckpointerType


def inspect_database(db_path="./data/checkpoints.db"):
    """Inspect all checkpoints in the database."""
    print(f"\n{'='*70}")
    print(f"📊 Checkpoint Database Inspector")
    print(f"{'='*70}")
    print(f"Database: {db_path}\n")
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        print("\nRun the system with checkpointing enabled first:")
        print("  python main.py")
        print("  Choose: Enable checkpointing? [Y/n]: Y")
        return
    
    manager = CheckpointManager(
        checkpointer_type=CheckpointerType.SQLITE,
        connection_string=db_path
    )
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Database statistics
    cursor.execute("SELECT COUNT(*) FROM checkpoints")
    total_checkpoints = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT thread_id) FROM checkpoints")
    total_threads = cursor.fetchone()[0]
    
    print(f"📈 Statistics:")
    print(f"  Total Checkpoints: {total_checkpoints}")
    print(f"  Total Threads: {total_threads}")
    print()
    
    # List all threads
    cursor.execute("""
        SELECT 
            thread_id,
            COUNT(*) as checkpoint_count,
            MAX(json_extract(metadata, '$.created_at')) as last_checkpoint
        FROM checkpoints
        GROUP BY thread_id
        ORDER BY last_checkpoint DESC
    """)
    
    threads = cursor.fetchall()
    
    if not threads:
        print("No threads found in database.")
        conn.close()
        return
    
    print(f"🧵 Threads (most recent first):\n")
    
    for i, (thread_id, checkpoint_count, last_checkpoint) in enumerate(threads, 1):
        print(f"{i}. Thread: {thread_id[:32]}...")
        print(f"   Checkpoints: {checkpoint_count}")
        if last_checkpoint:
            print(f"   Last Activity: {last_checkpoint}")
        
        # Get latest state for this thread
        try:
            state = manager.get_state(thread_id)
            if state:
                working = state.get("working", {})
                archive = state.get("archive", {})
                
                # Show key metrics
                entities = len(working.get("entities", []))
                tables = len(working.get("tables", []))
                llm_calls = archive.get("total_llm_calls", 0)
                has_ddl = bool(archive.get("ddl_script"))
                has_erd = bool(archive.get("erd_diagram"))
                has_nestjs = bool(archive.get("nestjs_architecture"))
                
                print(f"   State:")
                print(f"     • Entities: {entities}")
                print(f"     • Tables: {tables}")
                print(f"     • LLM Calls: {llm_calls}")
                print(f"     • DDL Script: {'✓' if has_ddl else '✗'}")
                print(f"     • ERD Diagram: {'✓' if has_erd else '✗'}")
                print(f"     • NestJS Architecture: {'✓' if has_nestjs else '✗'}")
                
                # Show current step
                current_step = working.get("current_step", "N/A")
                is_complete = working.get("is_complete", False)
                print(f"     • Current Step: {current_step}")
                print(f"     • Complete: {'✓' if is_complete else '✗'}")
        except Exception as e:
            print(f"   ⚠️  Could not load state: {e}")
        
        print()
    
    conn.close()
    
    print(f"\n{'='*70}")
    print("💡 Tips:")
    print("  - Use checkpoint_viewer.py for interactive exploration")
    print("  - Use DB Browser for SQLite to view raw data")
    print("  - See DATABASE_INSPECTION.md for more tools")
    print(f"{'='*70}\n")


def export_thread_state(thread_id: str, db_path="./data/checkpoints.db", output_file=None):
    """Export a thread's state to JSON."""
    manager = CheckpointManager(
        checkpointer_type=CheckpointerType.SQLITE,
        connection_string=db_path
    )
    
    state = manager.get_state(thread_id)
    
    if not state:
        print(f"❌ No state found for thread: {thread_id}")
        return
    
    if not output_file:
        output_file = f"state_{thread_id[:8]}.json"
    
    with open(output_file, 'w') as f:
        json.dump(state, f, indent=2, default=str)
    
    print(f"✅ Exported state to: {output_file}")
    
    # Show summary
    working = state.get("working", {})
    archive = state.get("archive", {})
    
    print(f"\n📊 State Summary:")
    print(f"  Entities: {len(working.get('entities', []))}")
    print(f"  Tables: {len(working.get('tables', []))}")
    print(f"  LLM Calls: {archive.get('total_llm_calls', 0)}")
    
    if archive.get("ddl_script"):
        ddl_file = f"schema_{thread_id[:8]}.sql"
        with open(ddl_file, 'w') as f:
            f.write(archive["ddl_script"])
        print(f"  DDL exported to: {ddl_file}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Inspect checkpoint database')
    parser.add_argument('--db', default='./data/checkpoints.db', help='Database path')
    parser.add_argument('--export', metavar='THREAD_ID', help='Export thread state to JSON')
    parser.add_argument('--output', help='Output file for export')
    
    args = parser.parse_args()
    
    if args.export:
        export_thread_state(args.export, args.db, args.output)
    else:
        inspect_database(args.db)


if __name__ == "__main__":
    main()

