#!/usr/bin/env python3
"""
Interactive Checkpoint Viewer

Browse and explore checkpoint data with an interactive CLI.
"""

import sys
import os
import json
import sqlite3
from typing import Optional

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


class CheckpointViewer:
    def __init__(self, db_path: str = "./data/checkpoints.db"):
        self.db_path = db_path
        self.manager = CheckpointManager(
            checkpointer_type=CheckpointerType.SQLITE,
            connection_string=db_path
        )
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
    
    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def list_threads(self):
        """List all threads with statistics."""
        print("\n" + "="*70)
        print("🧵 All Threads")
        print("="*70 + "\n")
        
        self.cursor.execute("""
            SELECT 
                thread_id,
                COUNT(*) as checkpoint_count,
                MAX(json_extract(metadata, '$.created_at')) as last_checkpoint
            FROM checkpoints
            GROUP BY thread_id
            ORDER BY last_checkpoint DESC
        """)
        
        threads = self.cursor.fetchall()
        
        if not threads:
            print("No threads found.")
            return []
        
        for i, (tid, count, last) in enumerate(threads, 1):
            print(f"{i}. {tid[:40]}...")
            print(f"   Checkpoints: {count} | Last: {last or 'N/A'}")
        
        print()
        return [t[0] for t in threads]
    
    def view_thread_checkpoints(self, thread_id: str):
        """View all checkpoints for a thread."""
        print("\n" + "="*70)
        print(f"💾 Checkpoints for Thread: {thread_id[:40]}...")
        print("="*70 + "\n")
        
        checkpoints = self.manager.list_checkpoints(thread_id, limit=100)
        
        if not checkpoints:
            print("No checkpoints found.")
            return []
        
        for i, cp in enumerate(checkpoints, 1):
            cp_id = cp.get('checkpoint_id', 'N/A')
            parent_id = cp.get('parent_checkpoint_id')
            created = cp.get('created_at', 'N/A')
            
            print(f"{i}. Checkpoint: {cp_id[:32] if cp_id != 'N/A' else 'N/A'}...")
            if parent_id:
                print(f"   Parent: {parent_id[:32]}...")
            print(f"   Created: {created}")
            
            metadata = cp.get('metadata', {})
            if metadata:
                step = metadata.get('step', 'N/A')
                print(f"   Step: {step}")
            print()
        
        return checkpoints
    
    def view_state(self, thread_id: str, checkpoint_id: Optional[str] = None):
        """View state at a checkpoint."""
        print("\n" + "="*70)
        print(f"📊 State Viewer")
        print("="*70 + "\n")
        
        state = self.manager.get_state(thread_id, checkpoint_id)
        
        if not state:
            print("❌ No state found.")
            return
        
        working = state.get("working", {})
        archive = state.get("archive", {})
        
        # Display summary
        print("📝 Working State:")
        print(f"  Current Step: {working.get('current_step', 'N/A')}")
        print(f"  SQL Dialect: {working.get('sql_dialect', 'N/A')}")
        print(f"  Is Complete: {working.get('is_complete', False)}")
        print(f"  Needs Clarification: {working.get('needs_clarification', False)}")
        
        entities = working.get('entities', [])
        print(f"\n  Entities ({len(entities)}):")
        for entity in entities[:5]:  # Show first 5
            print(f"    • {entity.get('name', 'N/A')}: {entity.get('description', '')[:50]}")
        if len(entities) > 5:
            print(f"    ... and {len(entities) - 5} more")
        
        tables = working.get('tables', [])
        print(f"\n  Tables ({len(tables)}):")
        for table in tables[:5]:  # Show first 5
            columns = len(table.get('columns', []))
            print(f"    • {table.get('name', 'N/A')} ({columns} columns)")
        if len(tables) > 5:
            print(f"    ... and {len(tables) - 5} more")
        
        print(f"\n📦 Archive State:")
        print(f"  Total Tasks: {len(archive.get('tasks', []))}")
        print(f"  Critic Reports: {len(archive.get('critic_reports', []))}")
        print(f"  LLM Calls: {archive.get('total_llm_calls', 0)}")
        print(f"  Has DDL: {'✓' if archive.get('ddl_script') else '✗'}")
        print(f"  Has ERD: {'✓' if archive.get('erd_diagram') else '✗'}")
        print(f"  Has NestJS: {'✓' if archive.get('nestjs_architecture') else '✗'}")
        
        return state
    
    def export_state(self, thread_id: str, output_file: str):
        """Export state to JSON file."""
        state = self.manager.get_state(thread_id)
        
        if not state:
            print("❌ No state found.")
            return
        
        with open(output_file, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        
        print(f"✅ State exported to: {output_file}")
    
    def export_ddl(self, thread_id: str, output_file: str):
        """Export DDL script to file."""
        state = self.manager.get_state(thread_id)
        
        if not state:
            print("❌ No state found.")
            return
        
        ddl = state.get("archive", {}).get("ddl_script")
        
        if not ddl:
            print("❌ No DDL script found in state.")
            return
        
        with open(output_file, 'w') as f:
            f.write(ddl)
        
        print(f"✅ DDL script exported to: {output_file}")
    
    def run(self):
        """Run interactive viewer."""
        print("\n" + "="*70)
        print("🔍 Interactive Checkpoint Viewer")
        print("="*70)
        
        current_thread = None
        
        while True:
            print("\n" + "-"*70)
            if current_thread:
                print(f"Current Thread: {current_thread[:40]}...")
            print("-"*70)
            
            print("\nOptions:")
            print("  1. List all threads")
            print("  2. Select thread")
            print("  3. View thread checkpoints")
            print("  4. View current state")
            print("  5. Export state to JSON")
            print("  6. Export DDL script")
            print("  7. Clear current thread")
            print("  8. Exit")
            
            choice = input("\nChoice: ").strip()
            
            if choice == "1":
                self.list_threads()
            
            elif choice == "2":
                threads = self.list_threads()
                if threads:
                    idx = input("Select thread number: ").strip()
                    try:
                        current_thread = threads[int(idx) - 1]
                        print(f"✓ Selected: {current_thread[:40]}...")
                    except (ValueError, IndexError):
                        print("❌ Invalid selection")
            
            elif choice == "3":
                if not current_thread:
                    print("❌ No thread selected. Use option 2 first.")
                else:
                    self.view_thread_checkpoints(current_thread)
            
            elif choice == "4":
                if not current_thread:
                    print("❌ No thread selected. Use option 2 first.")
                else:
                    self.view_state(current_thread)
            
            elif choice == "5":
                if not current_thread:
                    print("❌ No thread selected. Use option 2 first.")
                else:
                    filename = input("Output filename [state.json]: ").strip() or "state.json"
                    self.export_state(current_thread, filename)
            
            elif choice == "6":
                if not current_thread:
                    print("❌ No thread selected. Use option 2 first.")
                else:
                    filename = input("Output filename [schema.sql]: ").strip() or "schema.sql"
                    self.export_ddl(current_thread, filename)
            
            elif choice == "7":
                current_thread = None
                print("✓ Thread cleared")
            
            elif choice == "8":
                print("\nGoodbye! 👋")
                break
            
            else:
                print("❌ Invalid choice")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Interactive checkpoint viewer')
    parser.add_argument('--db', default='./data/checkpoints.db', help='Database path')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.db):
        print(f"❌ Database not found: {args.db}")
        print("\nRun the system with checkpointing enabled first:")
        print("  python main.py")
        return
    
    viewer = CheckpointViewer(args.db)
    viewer.run()


if __name__ == "__main__":
    main()

