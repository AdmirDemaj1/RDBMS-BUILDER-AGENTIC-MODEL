#!/usr/bin/env python3
"""
Installation Verification Script

Verifies that all checkpointing dependencies are installed correctly.
"""

import sys

def check_import(module_name, package_name=None):
    """Check if a module can be imported."""
    if package_name is None:
        package_name = module_name
    
    try:
        __import__(module_name)
        print(f"✅ {package_name}")
        return True
    except ImportError as e:
        print(f"❌ {package_name} - Not installed")
        print(f"   Error: {e}")
        return False


def main():
    """Main verification function."""
    print("\n" + "="*70)
    print("🔍 Checkpoint Installation Verifier")
    print("="*70 + "\n")
    
    print("Checking core dependencies...\n")
    
    results = {
        "Core": [
            ("langgraph", "langgraph"),
            ("langchain", "langchain"),
        ],
        "Checkpointing": [
            ("langgraph.checkpoint.sqlite", "langgraph-checkpoint-sqlite"),
            ("langgraph.checkpoint.postgres", "langgraph-checkpoint-postgres"),
            ("psycopg", "psycopg"),
        ],
        "Optional": [
            ("langsmith", "langsmith"),
        ]
    }
    
    all_passed = True
    missing_packages = []
    
    for category, checks in results.items():
        print(f"📦 {category}:")
        for module, package in checks:
            if not check_import(module, package):
                all_passed = False
                if category != "Optional":
                    missing_packages.append(package)
        print()
    
    # Test checkpoint manager
    print("🧪 Testing checkpoint manager...\n")
    
    try:
        # Test creating checkpointers directly without importing CheckpointManager
        # to avoid circular import issues in standalone script
        
        # Test Memory checkpointer
        try:
            from langgraph.checkpoint.memory import MemorySaver
            mem_cp = MemorySaver()
            print("✅ Memory checkpointer can be created")
        except Exception as e:
            print(f"⚠️  Memory checkpointer error: {e}")
        
        # Test SQLite checkpointer
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            sqlite_cp = SqliteSaver.from_conn_string(":memory:")
            print("✅ SQLite checkpointer can be created")
        except Exception as e:
            print(f"⚠️  SQLite checkpointer error: {e}")
        
        # Test PostgreSQL checkpointer (just import, don't connect)
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            print("✅ PostgreSQL checkpointer can be imported")
        except Exception as e:
            print(f"⚠️  PostgreSQL checkpointer import error: {e}")
        
    except Exception as e:
        print(f"❌ Checkpointer test failed: {e}")
        all_passed = False
    
    print()
    print("="*70)
    
    if all_passed:
        print("✅ All checks passed! Checkpointing is ready to use.")
        print("\nNext steps:")
        print("  1. Run: python main.py")
        print("  2. Enable checkpointing when prompted")
        print("  3. View your data: python scripts/inspect_checkpoints.py")
    else:
        print("❌ Some checks failed.")
        if missing_packages:
            print("\nInstall missing packages:")
            print("  pip install " + " ".join(missing_packages))
            print("\nOr install everything:")
            print("  pip install -e .")
    
    print("="*70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

