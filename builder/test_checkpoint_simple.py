#!/usr/bin/env python3
"""Simple test to verify checkpointer creation works correctly."""

from langgraph.checkpoint.sqlite import SqliteSaver

print("=" * 70)
print("Testing LangGraph SqliteSaver")
print("=" * 70)

# Test 1: Context manager (returns context manager)
print("\nTest 1: Using from_conn_string() directly")
context_manager = SqliteSaver.from_conn_string(":memory:")
print(f"  Type: {type(context_manager).__name__}")
print(f"  Is context manager: {hasattr(context_manager, '__enter__')}")

# Test 2: Enter the context manager to get actual checkpointer
print("\nTest 2: Entering context manager")
with SqliteSaver.from_conn_string(":memory:") as checkpointer:
    print(f"  Checkpointer type: {type(checkpointer).__name__}")
    print(f"  Checkpointer module: {type(checkpointer).__module__}")
    
    # Check if it has the required methods
    required_methods = ['get_next_version', 'get_tuple', 'put', 'list']
    print("\n  Checking required methods:")
    for method in required_methods:
        has_method = hasattr(checkpointer, method)
        print(f"    Has {method}: {'✓' if has_method else '✗'}")
    
    if all(hasattr(checkpointer, m) for m in required_methods):
        print("\n  ✅ Checkpointer has all required methods!")
    else:
        print("\n  ❌ Checkpointer is missing required methods!")

print("\n" + "=" * 70)
print("Test completed!")
print("=" * 70)

