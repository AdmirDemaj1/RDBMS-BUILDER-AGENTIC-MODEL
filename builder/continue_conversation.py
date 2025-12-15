#!/usr/bin/env python3
"""
Continue Previous Conversation

This script allows you to easily resume a previous RDBMS builder conversation
from a checkpoint and add new requirements or modifications.
"""

from main import run_builder, list_previous_threads, select_previous_thread
from .utils.checkpoint_manager import CheckpointerType
import sys


def main():
    print("\n" + "=" * 70)
    print("🔄 CONTINUE PREVIOUS CONVERSATION")
    print("=" * 70)
    
    # Configuration
    checkpoint_type = CheckpointerType.SQLITE
    checkpoint_connection = None
    
    print("\nCheckpoint configuration:")
    cpt = input("Checkpoint type [1=SQLite (default), 2=PostgreSQL]: ").strip()
    if cpt == "2":
        checkpoint_type = CheckpointerType.POSTGRES
        checkpoint_connection = input("PostgreSQL URI: ").strip()
    else:
        checkpoint_type = CheckpointerType.SQLITE
        checkpoint_connection = input("SQLite DB path [./data/checkpoints.db]: ").strip() or None
    
    # Select thread
    thread_id = select_previous_thread(checkpoint_type, checkpoint_connection)
    
    if not thread_id:
        print("\n❌ No thread selected. Exiting.")
        sys.exit(0)
    
    print(f"\n✅ Selected thread: {thread_id[:16]}...")
    
    # Get additional requirements
    print("\n" + "=" * 70)
    print("What would you like to do?")
    print("=" * 70)
    print("1. Add new tables/features")
    print("2. Modify existing schema")
    print("3. Generate additional outputs")
    print("4. Just regenerate with existing requirements")
    
    choice = input("\nChoice [1-4]: ").strip()
    
    if choice in ["1", "2", "3"]:
        requirements = input("\nDescribe your changes:\n> ").strip()
        if not requirements:
            print("❌ No requirements provided. Exiting.")
            sys.exit(0)
    else:
        requirements = "Continue with existing requirements"
    
    # Additional configuration
    print("\n" + "=" * 70)
    print("Additional Configuration")
    print("=" * 70)
    
    d = input("Dialect [1=PostgreSQL, 2=MySQL, 3=SQLite, Enter=keep previous]: ").strip()
    dialect = {"1": "postgresql", "2": "mysql", "3": "sqlite"}.get(d, "postgresql")
    
    c = input("Enable critic? [Y/n]: ").strip().lower()
    enable_critic = c != "n"
    
    n = input("Generate NestJS backend? [Y/n]: ").strip().lower()
    generate_nestjs = n != "n"
    
    print("\n" + "=" * 70)
    print("🚀 CONTINUING CONVERSATION...")
    print("=" * 70)
    
    # Run with resumed thread
    result = run_builder(
        requirements=requirements,
        dialect=dialect,
        enable_critic=enable_critic,
        generate_nestjs=generate_nestjs,
        interactive=True,
        thread_id=thread_id,  # Resume this thread
        enable_checkpointing=True,
        checkpoint_type=checkpoint_type,
        checkpoint_connection=checkpoint_connection
    )
    
    # Show results
    print("\n" + "=" * 70)
    print("📄 RESULTS")
    print("=" * 70)
    
    archive = result.get("archive", {})
    working = result.get("working", {})
    
    print(f"\nEntities: {len(working.get('entities', []))}")
    print(f"Tables: {len(working.get('tables', []))}")
    print(f"LLM Calls: {archive.get('total_llm_calls', 0)}")
    
    if archive.get("ddl_script"):
        print("\n📄 DDL Script generated")
        preview = archive["ddl_script"][:500]
        print(preview)
        if len(archive["ddl_script"]) > 500:
            print("... (truncated)")
    
    # Save option
    save = input("\n💾 Save outputs? [Y/n]: ").strip().lower()
    if save != "n":
        from main import save_outputs
        save_outputs(result)
        print("✅ Outputs saved!")
    
    print("\n" + "=" * 70)
    print("✨ CONVERSATION CONTINUED SUCCESSFULLY!")
    print(f"🧵 Thread ID: {thread_id[:16]}...")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

