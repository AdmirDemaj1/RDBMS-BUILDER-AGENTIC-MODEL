"""
Parent Graph Runner
Interactive CLI for running the full workflow

The parent graph uses LLM to route user requests:
- "Build a hotel system" → Backend Builder
- "Explain the database schema" → Explainer
"""
import os
import sys
import uuid
from typing import Optional, List

from parent_graph.state import (
    ParentGraphState,
    WorkflowMode,
    EnhancementType,
    create_initial_parent_state
)
from parent_graph.builder import build_parent_graph
from parent_graph.memory import (
    create_memory_manager,
    MemoryScope,
    resume_conversation,
    list_and_select_conversation
)


def print_header():
    print("\n" + "=" * 80)
    print("🏗️  INTELLIGENT BACKEND ASSISTANT")
    print("    Build backends or ask questions about them")
    print("=" * 80)


def print_results(state: ParentGraphState):
    """Print final results"""
    print("\n" + "=" * 80)
    print("📊 EXECUTION SUMMARY")
    print("=" * 80)
    
    working = state["working"]
    archive = state["archive"]
    
    # Show what was routed
    if working.get("user_intent"):
        print(f"\n🔍 Intent: {working['user_intent']}")
        if working.get("intent_reasoning"):
            print(f"   Reason: {working['intent_reasoning']}")
    
    print(f"✅ Total LLM Calls: {archive.get('total_llm_calls', 0)}")
    print(f"✅ Versions Generated: {len(archive.get('versions', []))}")
    
    # Subgraph execution summary
    executions = working.get("subgraph_executions", [])
    if executions:
        print("\n📦 Subgraph Executions:")
        for exec in executions:
            status_icon = "✅" if exec["status"].value == "completed" else "❌"
            print(f"  {status_icon} {exec['name']}: {exec['status'].value} ({exec['llm_calls']} LLM calls)")
    
    # Show final outputs preview
    if archive.get("final_ddl_script"):
        lines = archive["final_ddl_script"].split('\n')
        print(f"\n📄 DDL Script: {len(lines)} lines")
        print("  " + "\n  ".join(lines[:5]))
        if len(lines) > 5:
            print(f"  ... ({len(lines) - 5} more lines)")


def save_outputs(state: ParentGraphState, output_dir: str = "output/parent_graph"):
    """Save all outputs to files"""
    os.makedirs(output_dir, exist_ok=True)
    
    archive = state["archive"]
    
    if archive["final_ddl_script"]:
        path = os.path.join(output_dir, "schema.sql")
        with open(path, "w") as f:
            f.write(archive["final_ddl_script"])
        print(f"\n📄 Saved DDL: {path}")
    
    if archive["final_erd_diagram"]:
        path = os.path.join(output_dir, "erd.md")
        with open(path, "w") as f:
            f.write("# Entity Relationship Diagram\n\n```mermaid\n")
            f.write(archive["final_erd_diagram"])
            f.write("\n```\n")
        print(f"📊 Saved ERD: {path}")
    
    if archive["final_nestjs_architecture"]:
        import json
        path = os.path.join(output_dir, "nestjs_architecture.json")
        with open(path, "w") as f:
            json.dump(archive["final_nestjs_architecture"], f, indent=2)
        print(f"🚀 Saved NestJS Architecture: {path}")


def run_parent_graph(
    user_input: str,
    enable_memory: bool = True,
    memory_type: str = "sqlite",
    db_path: Optional[str] = None,
    resume_thread_id: Optional[str] = None,
    existing_state: Optional[ParentGraphState] = None
) -> ParentGraphState:
    """
    Run the parent graph with intelligent routing.
    
    The LLM will analyze user input and route to:
    - Backend Builder: For building/modifying backends
    - Explainer: For questions about generated backends
    """
    print_header()
    print(f"💾 Memory: {'Enabled' if enable_memory else 'Disabled'} ({memory_type})")
    
    # Initialize memory manager
    memory_manager = None
    parent_checkpointer = None
    
    if enable_memory:
        memory_manager = create_memory_manager(
            checkpointer_type=memory_type,
            db_path=db_path or "./data/parent_graph_memory.db"
        )
        parent_checkpointer = memory_manager.get_checkpointer(MemoryScope.PARENT)
        print(f"✅ Memory manager initialized")
    
    # Create or resume thread
    thread_id = resume_thread_id or str(uuid.uuid4())
    print(f"🧵 Thread: {thread_id[:8]}...")
    print("=" * 80)
    
    # Use existing state if provided, otherwise create new
    if existing_state:
        state = existing_state
        # Update the requirements with new user input
        state["working"]["initial_requirements"] = user_input
        print("\n✅ Using existing session state")
    else:
        state = create_initial_parent_state(
            requirements=user_input,
            mode=WorkflowMode.BUILD_ONLY,
            thread_id=thread_id
        )
        print("\n✅ Created new state")
    
    # Build parent graph with LLM routing
    parent_graph = build_parent_graph(
        checkpointer=parent_checkpointer,
        interactive=True
    )
    
    # Create config
    config = {
        "configurable": {
            "thread_id": thread_id,
            "scope": MemoryScope.PARENT.value
        }
    }
    
    print("\n🚀 Processing your request...\n")
    
    try:
        final_state = parent_graph.invoke(state, config=config)
        
        print("\n" + "=" * 80)
        print("🎉 COMPLETE!")
        print("=" * 80)
        
        return final_state
        
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        if memory_manager:
            memory_manager.cleanup()


def main():
    """Interactive main function with conversational loop"""
    print("\n🔧 CONFIGURATION")
    print("-" * 80)
    
    # Memory configuration
    mem = input("Enable long-term memory? [Y/n]: ").strip().lower()
    enable_memory = mem != "n"
    
    memory_type = "sqlite"
    db_path = None
    resume_thread_id = None
    
    if enable_memory:
        mt = input("Memory type [1=SQLite (default), 2=Memory]: ").strip()
        memory_type = "memory" if mt == "2" else "sqlite"
        
        if memory_type == "sqlite":
            db_path = input("Database path [./data/parent_graph_memory.db]: ").strip()
            db_path = db_path or None
            
            resume = input("\nResume previous conversation? [y/N]: ").strip().lower()
            if resume == "y":
                temp_manager = create_memory_manager(memory_type, db_path)
                resume_thread_id = list_and_select_conversation(temp_manager, MemoryScope.PARENT)
                temp_manager.cleanup()
    
    print("\n" + "=" * 80)
    print("🤖 INTELLIGENT BACKEND ASSISTANT")
    print("=" * 80)
    print("\nExamples:")
    print('  • "Build a hotel management system"')
    print('  • "Explain the database schema"')
    print('  • "What tables are in the database?"')
    print("\nType 'quit' or 'exit' to end the session.")
    print("-" * 80)
    
    # Maintain state across conversation
    current_state = None
    
    while True:
        print("\n📝 What would you like to do?")
        user_input = input("> ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() in ["quit", "exit", "q"]:
            print("\n👋 Goodbye!")
            break
        
        # Run the graph - LLM will route to appropriate subgraph
        result = run_parent_graph(
            user_input=user_input,
            enable_memory=enable_memory,
            memory_type=memory_type,
            db_path=db_path,
            resume_thread_id=resume_thread_id,
            existing_state=current_state
        )
        
        # Keep state for next iteration
        current_state = result
        
        # Print results
        print_results(result)
        
        # Offer to save if we have outputs
        if result["archive"].get("final_ddl_script"):
            save_choice = input("\n💾 Save outputs? [y/N]: ").strip().lower()
            if save_choice == "y":
                save_outputs(result)
    
    print("\n✨ Session ended!\n")


if __name__ == "__main__":
    main()