#!/usr/bin/env python3
"""
LangGraph Checkpointing Demo

This example demonstrates the long-term memory capabilities using LangGraph checkpointing:
1. Basic checkpointing with SQLite
2. Resuming from checkpoints
3. Listing checkpoint history
4. Time-travel debugging
5. Multi-session conversations
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import run_builder, list_checkpoints, resume_from_checkpoint
from ..utils.checkpoint_manager import CheckpointManager, CheckpointerType
from ..utils.thread_manager import get_or_create_thread_id


def demo_basic_checkpointing():
    """Demo 1: Basic checkpointing with persistence."""
    print("\n" + "=" * 70)
    print("DEMO 1: Basic Checkpointing with SQLite")
    print("=" * 70)
    
    requirements = """
    Build a simple blog system with:
    - Users can create accounts
    - Users can write blog posts
    - Users can comment on posts
    - Posts can have tags
    """
    
    # Run with checkpointing enabled
    thread_id = get_or_create_thread_id()
    
    result = run_builder(
        requirements=requirements,
        dialect="postgresql",
        enable_critic=False,  # Disable for faster demo
        generate_nestjs=False,
        interactive=False,
        thread_id=thread_id,
        enable_checkpointing=True,
        checkpoint_type=CheckpointerType.SQLITE,
        checkpoint_connection="./data/demo_checkpoints.db"
    )
    
    print(f"\n✅ Completed with checkpointing!")
    print(f"Thread ID: {thread_id}")
    
    # List checkpoints created
    list_checkpoints(
        thread_id=thread_id,
        checkpoint_type=CheckpointerType.SQLITE,
        connection_string="./data/demo_checkpoints.db",
        limit=10
    )
    
    return thread_id


def demo_resume_from_checkpoint(thread_id: str):
    """Demo 2: Resume from a checkpoint."""
    print("\n" + "=" * 70)
    print("DEMO 2: Resume from Checkpoint")
    print("=" * 70)
    
    # Resume and inspect state
    state = resume_from_checkpoint(
        thread_id=thread_id,
        checkpoint_type=CheckpointerType.SQLITE,
        connection_string="./data/demo_checkpoints.db"
    )
    
    if state:
        print("\n📊 State Summary:")
        working = state.get("working", {})
        archive = state.get("archive", {})
        
        print(f"  Entities: {len(working.get('entities', []))}")
        print(f"  Tables: {len(working.get('tables', []))}")
        print(f"  LLM Calls: {archive.get('total_llm_calls', 0)}")
        
        if archive.get("ddl_script"):
            print(f"\n📄 DDL Script Available: {len(archive['ddl_script'])} characters")


def demo_multi_session():
    """Demo 3: Multi-session conversation with same thread."""
    print("\n" + "=" * 70)
    print("DEMO 3: Multi-Session Conversation")
    print("=" * 70)
    
    thread_id = get_or_create_thread_id()
    
    # Session 1: Initial requirements
    print("\n📍 Session 1: Initial Schema")
    requirements_1 = """
    Build an e-commerce system with:
    - Products with inventory
    - Shopping carts
    - Orders
    """
    
    result1 = run_builder(
        requirements=requirements_1,
        dialect="postgresql",
        enable_critic=False,
        generate_nestjs=False,
        interactive=False,
        thread_id=thread_id,
        enable_checkpointing=True,
        checkpoint_type=CheckpointerType.SQLITE,
        checkpoint_connection="./data/demo_checkpoints.db"
    )
    
    print(f"\nSession 1 complete. Thread: {thread_id[:8]}...")
    print(f"Tables created: {len(result1['working'].get('tables', []))}")
    
    # Session 2: Additional requirements (using same thread)
    print("\n📍 Session 2: Extended Schema")
    requirements_2 = """
    Extend the e-commerce system with:
    - Product reviews and ratings
    - Wishlist functionality
    - Coupon codes and discounts
    """
    
    result2 = run_builder(
        requirements=requirements_2,
        dialect="postgresql",
        enable_critic=False,
        generate_nestjs=False,
        interactive=False,
        thread_id=thread_id,  # Same thread ID!
        enable_checkpointing=True,
        checkpoint_type=CheckpointerType.SQLITE,
        checkpoint_connection="./data/demo_checkpoints.db"
    )
    
    print(f"\nSession 2 complete. Thread: {thread_id[:8]}...")
    print(f"Tables created: {len(result2['working'].get('tables', []))}")
    
    # Show checkpoint history across both sessions
    list_checkpoints(
        thread_id=thread_id,
        checkpoint_type=CheckpointerType.SQLITE,
        connection_string="./data/demo_checkpoints.db",
        limit=20
    )


def demo_checkpoint_manager_api():
    """Demo 4: Using CheckpointManager API directly."""
    print("\n" + "=" * 70)
    print("DEMO 4: CheckpointManager API")
    print("=" * 70)
    
    # Initialize checkpoint manager
    checkpoint_manager = CheckpointManager(
        checkpointer_type=CheckpointerType.SQLITE,
        connection_string="./data/demo_checkpoints.db"
    )
    
    # Create a simple thread for testing
    thread_id = get_or_create_thread_id()
    
    print(f"\n📝 Thread ID: {thread_id[:8]}...")
    
    # Use checkpoint manager context
    with checkpoint_manager.get_checkpointer() as checkpointer:
        print(f"✅ Checkpointer initialized: {type(checkpointer).__name__}")
        
        # Create config for this thread
        config = CheckpointManager.create_thread_config(thread_id)
        print(f"✅ Thread config created: {config}")
    
    print("\n✅ Checkpointer context closed automatically")


def demo_error_recovery():
    """Demo 5: Error recovery with checkpointing."""
    print("\n" + "=" * 70)
    print("DEMO 5: Error Recovery")
    print("=" * 70)
    
    print("""
    Checkpointing enables automatic error recovery:
    
    1. Each node execution creates a checkpoint
    2. If a node fails, the graph can resume from the last successful checkpoint
    3. No need to re-execute completed nodes
    4. State is preserved across failures
    
    Benefits:
    - Fault tolerance
    - Reduced API costs (no redundant LLM calls)
    - Faster recovery
    - Better user experience
    
    Try it: Run a long workflow, interrupt it (Ctrl+C), then resume using the same thread_id!
    """)


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("🚀 LangGraph Checkpointing Demo Suite")
    print("=" * 70)
    
    print("\nAvailable demos:")
    print("1. Basic Checkpointing")
    print("2. Resume from Checkpoint")
    print("3. Multi-Session Conversation")
    print("4. CheckpointManager API")
    print("5. Error Recovery (info)")
    print("6. Run All Demos")
    
    choice = input("\nSelect demo (1-6): ").strip()
    
    if choice == "1":
        thread_id = demo_basic_checkpointing()
        print(f"\n💡 Tip: Use thread_id={thread_id} to resume this session!")
    
    elif choice == "2":
        thread_id = input("Enter thread_id to resume: ").strip()
        if thread_id:
            demo_resume_from_checkpoint(thread_id)
        else:
            print("❌ Thread ID required")
    
    elif choice == "3":
        demo_multi_session()
    
    elif choice == "4":
        demo_checkpoint_manager_api()
    
    elif choice == "5":
        demo_error_recovery()
    
    elif choice == "6":
        print("\n🏃 Running all demos...")
        thread_id = demo_basic_checkpointing()
        demo_resume_from_checkpoint(thread_id)
        demo_multi_session()
        demo_checkpoint_manager_api()
        demo_error_recovery()
        print("\n✅ All demos completed!")
    
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    main()

