"""
Quick Start Examples: Three Approaches to Subgraph Integration
"""
import sys
from typing import Dict, Any

from langgraph.graph import StateGraph, END
from parent_graph.state import ParentGraphState, create_initial_parent_state, WorkflowMode
from parent_graph.memory import create_memory_manager, MemoryScope
from builder.graph.subgraph import create_rdbms_node_with_state_mapping, RDBMSBuilderInput, RDBMSBuilderOutput


# ============================================================
# APPROACH A: SUBGRAPH NODES (RECOMMENDED)
# ============================================================

def approach_a_subgraph_nodes():
    """Approach A: Use wrapped node function with state mapping"""
    print("\n" + "=" * 80)
    print("APPROACH A: SUBGRAPH NODES (RECOMMENDED)")
    print("=" * 80)
    
    # Setup memory
    memory_manager = create_memory_manager("memory")
    builder_cp = memory_manager.get_checkpointer(MemoryScope.BUILDER)
    parent_cp = memory_manager.get_checkpointer(MemoryScope.PARENT)
    
    # Define state mappers for parent <-> subgraph
    def input_mapper(parent_state: Dict[str, Any]) -> RDBMSBuilderInput:
        """Extract subgraph input from parent state"""
        working = parent_state.get("working", {})
        return RDBMSBuilderInput(
            user_requirements=working.get("initial_requirements", ""),
            sql_dialect="postgresql",
            enable_critic=True,
            generate_nestjs=True,
            thread_id=working.get("builder_thread_id")
        )
    
    def output_mapper(rdbms_output: RDBMSBuilderOutput) -> Dict[str, Any]:
        """Transform subgraph output to parent state updates"""
        return {
            "working": {
                "backend_state": {
                    "ddl_script": rdbms_output.get("ddl_script", ""),
                    "erd_diagram": rdbms_output.get("erd_diagram", ""),
                    "is_complete": rdbms_output.get("is_complete", False)
                }
            },
            "archive": {
                "final_ddl_script": rdbms_output.get("ddl_script", ""),
                "final_erd_diagram": rdbms_output.get("erd_diagram", "")
            }
        }
    
    # Create wrapped node with state mapping
    backend_builder_node = create_rdbms_node_with_state_mapping(
        checkpointer=builder_cp,
        input_mapper=input_mapper,
        output_mapper=output_mapper,
        auto_continue=True
    )
    
    # Build parent graph
    parent_workflow = StateGraph(ParentGraphState)
    
    def prepare_builder(state: ParentGraphState) -> dict:
        print("  📦 Preparing builder subgraph...")
        return {"working": {"current_subgraph": "backend_builder"}}
    
    def process_results(state: ParentGraphState) -> dict:
        print("  ✅ Processing builder results...")
        return {"working": {"is_complete": True}}
    
    # Add nodes
    parent_workflow.add_node("prepare_builder", prepare_builder)
    parent_workflow.add_node("backend_builder", backend_builder_node)  # ← Wrapped node with state mapping!
    parent_workflow.add_node("process_results", process_results)
    
    # Connect
    parent_workflow.set_entry_point("prepare_builder")
    parent_workflow.add_edge("prepare_builder", "backend_builder")
    parent_workflow.add_edge("backend_builder", "process_results")
    parent_workflow.add_edge("process_results", END)
    
    # Compile
    parent_graph = parent_workflow.compile(checkpointer=parent_cp)
    
    # Test
    state = create_initial_parent_state(
        requirements="Build a simple blog with posts and comments",
        mode=WorkflowMode.BUILD_ONLY
    )
    
    config = {"configurable": {"thread_id": "test-a"}}
    result = parent_graph.invoke(state, config=config)
    
    print(f"\n  ✅ Complete! DDL length: {len(result['archive'].get('final_ddl_script', '') or '')} chars")
    
    memory_manager.cleanup()


def main():
    """Run approach A example"""
    print("\n🚀 SUBGRAPH INTEGRATION EXAMPLE")
    
    try:
        approach_a_subgraph_nodes()
        print("\n✅ Example complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()