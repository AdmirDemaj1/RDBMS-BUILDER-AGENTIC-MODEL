#!/usr/bin/env python3
"""
View Full Checkpoint Structure

This script decodes the BLOB data from checkpoints and shows the complete structure.
"""

import sqlite3
import json
import sys
import os
from pprint import pprint

# Import LangGraph checkpointer to use its deserializer
from langgraph.checkpoint.sqlite import SqliteSaver

def view_checkpoint_structure(db_path="./data/checkpoints.db", thread_id=None, limit=1):
    """View the complete structure of checkpoints."""
    
    print("=" * 80)
    print(f"CHECKPOINT STRUCTURE VIEWER")
    print("=" * 80)
    
    # Use LangGraph's checkpointer to properly load data
    try:
        with SqliteSaver.from_conn_string(db_path) as checkpointer:
            # Get thread_id if not provided
            if not thread_id:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT thread_id FROM checkpoints LIMIT 1")
                result = cursor.fetchone()
                conn.close()
                
                if not result:
                    print("\nNo checkpoints found in database.")
                    return
                thread_id = result[0]
            
            print(f"\nThread ID: {thread_id[:40]}...")
            
            # Get checkpoint count
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?", (thread_id,))
            total = cursor.fetchone()[0]
            print(f"Total Checkpoints: {total}")
            print()
            
            # Get checkpoint metadata
            cursor.execute("""
                SELECT 
                    checkpoint_id,
                    parent_checkpoint_id,
                    metadata
                FROM checkpoints
                WHERE thread_id = ?
                ORDER BY rowid
                LIMIT ?
            """, (thread_id, limit))
            
            checkpoint_infos = cursor.fetchall()
            conn.close()
            
            # Use checkpointer to get actual checkpoint data
            config = {"configurable": {"thread_id": thread_id}}
            
            for i, (cp_id, parent_id, metadata_blob) in enumerate(checkpoint_infos, 1):
                print("=" * 80)
                print(f"CHECKPOINT #{i}")
                print("=" * 80)
                
                # Show basic info
                print(f"\nCheckpoint ID: {cp_id}")
                if parent_id:
                    print(f"Parent ID: {parent_id}")
                
                # Decode metadata (it's JSON)
                try:
                    if isinstance(metadata_blob, str):
                        metadata = json.loads(metadata_blob)
                    elif isinstance(metadata_blob, bytes):
                        metadata = json.loads(metadata_blob.decode('utf-8'))
                    else:
                        metadata = metadata_blob
                    
                    print(f"\nMetadata:")
                    print(f"  Source: {metadata.get('source', 'N/A')}")
                    print(f"  Step: {metadata.get('step', 'N/A')}")
                    if 'session_id' in metadata:
                        print(f"  Session ID: {metadata['session_id'][:40]}...")
                except Exception as e:
                    print(f"\n⚠️  Could not decode metadata: {e}")
                
                # Get checkpoint data using checkpointer API
                try:
                    checkpoint_config = {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_id": cp_id
                        }
                    }
                    
                    checkpoint_tuple = checkpointer.get_tuple(checkpoint_config)
                    
                    if not checkpoint_tuple:
                        print("\n⚠️  Could not load checkpoint data")
                        continue
                    
                    checkpoint_data = checkpoint_tuple.checkpoint
                    
                    print(f"\n{'─' * 80}")
                    print("CHECKPOINT DATA STRUCTURE:")
                    print('─' * 80)
                    
                    # Show top-level keys
                    if isinstance(checkpoint_data, dict):
                        print(f"\nTop-level keys: {list(checkpoint_data.keys())}")
                        
                        # Show channel_values (the actual GraphState)
                        if 'channel_values' in checkpoint_data:
                            channel_values = checkpoint_data['channel_values']
                            print(f"\n{'─' * 80}")
                            print("GRAPH STATE (channel_values):")
                            print('─' * 80)
                            
                            if isinstance(channel_values, dict):
                                # Show state structure
                                for key, value in channel_values.items():
                                    print(f"\n[{key}]")
                                    if isinstance(value, dict):
                                        # Show nested structure
                                        for subkey in value.keys():
                                            subvalue = value[subkey]
                                            if isinstance(subvalue, list):
                                                print(f"  • {subkey}: list with {len(subvalue)} items")
                                            elif isinstance(subvalue, dict):
                                                print(f"  • {subkey}: dict with {len(subvalue)} keys")
                                            elif isinstance(subvalue, str) and len(subvalue) > 100:
                                                print(f"  • {subkey}: string ({len(subvalue)} chars)")
                                            else:
                                                print(f"  • {subkey}: {type(subvalue).__name__} = {subvalue}")
                                    elif isinstance(value, list):
                                        print(f"  List with {len(value)} items")
                                    else:
                                        print(f"  {type(value).__name__}")
                                
                                # Show detailed content for working and archive
                                if 'working' in channel_values:
                                    print(f"\n{'─' * 80}")
                                    print("WORKING STATE DETAILS:")
                                    print('─' * 80)
                                    working = channel_values['working']
                                    
                                    if 'entities' in working and working['entities']:
                                        print(f"\nEntities ({len(working['entities'])}):")
                                        for entity in working['entities'][:3]:  # Show first 3
                                            print(f"  • {entity.get('name', 'N/A')}")
                                        if len(working['entities']) > 3:
                                            print(f"  ... and {len(working['entities']) - 3} more")
                                    
                                    if 'tables' in working and working['tables']:
                                        print(f"\nTables ({len(working['tables'])}):")
                                        for table in working['tables'][:3]:  # Show first 3
                                            cols = len(table.get('columns', []))
                                            print(f"  • {table.get('name', 'N/A')} ({cols} columns)")
                                        if len(working['tables']) > 3:
                                            print(f"  ... and {len(working['tables']) - 3} more")
                                    
                                    print(f"\nCurrent Step: {working.get('current_step', 'N/A')}")
                                    print(f"Is Complete: {working.get('is_complete', False)}")
                                
                                if 'archive' in channel_values:
                                    print(f"\n{'─' * 80}")
                                    print("ARCHIVE STATE DETAILS:")
                                    print('─' * 80)
                                    archive = channel_values['archive']
                                    
                                    print(f"Total Tasks: {len(archive.get('tasks', []))}")
                                    print(f"Critic Reports: {len(archive.get('critic_reports', []))}")
                                    print(f"LLM Calls: {archive.get('total_llm_calls', 0)}")
                                    print(f"Has DDL: {'Yes' if archive.get('ddl_script') else 'No'}")
                                    print(f"Has ERD: {'Yes' if archive.get('erd_diagram') else 'No'}")
                                    print(f"Has NestJS: {'Yes' if archive.get('nestjs_architecture') else 'No'}")
                        
                        # Show other checkpoint data
                        for key in checkpoint_data.keys():
                            if key != 'channel_values':
                                print(f"\n[{key}]: {type(checkpoint_data[key]).__name__}")
                    
                    else:
                        print(f"\nCheckpoint data type: {type(checkpoint_data)}")
                        pprint(checkpoint_data)
                
                except Exception as e:
                    print(f"\n⚠️  Could not decode checkpoint data: {e}")
                    import traceback
                    traceback.print_exc()
                
                print()
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 80)
    print("\n💡 Tips:")
    print("  - Export full state: python scripts/inspect_checkpoints.py --export THREAD_ID")
    print("  - Interactive viewer: python scripts/checkpoint_viewer.py")
    print("=" * 80)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='View full checkpoint structure')
    parser.add_argument('--db', default='./data/checkpoints.db', help='Database path')
    parser.add_argument('--thread', help='Thread ID to view')
    parser.add_argument('--limit', type=int, default=1, help='Number of checkpoints to show')
    parser.add_argument('--all', action='store_true', help='Show all checkpoints for thread')
    
    args = parser.parse_args()
    
    limit = 999999 if args.all else args.limit
    
    view_checkpoint_structure(args.db, args.thread, limit)


if __name__ == "__main__":
    main()

