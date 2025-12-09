# main.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# LangSmith tracing configuration (uses LANGSMITH_API_KEY from .env)
os.environ["LANGSMITH_TRACING"] = "true"
if not os.environ.get("LANGSMITH_PROJECT"):
    os.environ["LANGSMITH_PROJECT"] = "pr-downright-mainstream-28"

from graph.builder import graph, graph_after_clarification
from graph.state import GraphState
from typing import Optional


def get_initial_state(
    requirements: str,
    dialect: str = "postgresql",
    user_answers: Optional[list] = None
) -> GraphState:
    """Create initial state for the graph."""
    return {
        "user_requirements": requirements,
        "user_answers": user_answers or [],
        "sql_dialect": dialect,
        "clarifying_questions": [],
        "needs_clarification": False,
        "entities": [],
        "relationships": [],
        "tables": [],
        "validation_issues": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "ddl_script": "",
        "erd_diagram": "",
        "current_step": "start",
        "is_complete": False,
        "error": None
    }


def print_questions(questions: list) -> None:
    """Print clarifying questions in a nice format."""
    print("\n" + "=" * 60)
    print("❓ CLARIFICATION NEEDED")
    print("=" * 60)
    
    for i, q in enumerate(questions, 1):
        print(f"\n{i}. {q['question']}")
        print(f"   Context: {q['context']}")
        if q.get('options'):
            print(f"   Options: {', '.join(q['options'])}")
    
    print("\n" + "=" * 60)


def get_user_answers(questions: list) -> list:
    """Interactively get answers from user."""
    answers = []
    print("\nPlease answer the following questions (or press Enter to skip):\n")
    
    for i, q in enumerate(questions, 1):
        print(f"Q{i}: {q['question']}")
        if q.get('options'):
            print(f"    Suggested options: {', '.join(q['options'])}")
        
        answer = input(f"A{i}: ").strip()
        if answer:
            answers.append(f"Q: {q['question']} A: {answer}")
    
    return answers


def save_outputs(state: GraphState, output_dir: str = "output") -> None:
    """Save generated outputs to files."""
    os.makedirs(output_dir, exist_ok=True)
    
    dialect = state.get('sql_dialect', 'postgresql')
    
    # Save DDL
    ddl_file = os.path.join(output_dir, f"schema_{dialect}.sql")
    with open(ddl_file, 'w') as f:
        f.write(state['ddl_script'])
    print(f"📄 DDL saved to: {ddl_file}")
    
    # Save ERD
    if state.get('erd_diagram'):
        erd_file = os.path.join(output_dir, "erd_diagram.mmd")
        with open(erd_file, 'w') as f:
            f.write(state['erd_diagram'])
        print(f"📊 ERD saved to: {erd_file}")
        
        # Also save as markdown for easy viewing
        erd_md_file = os.path.join(output_dir, "erd_diagram.md")
        with open(erd_md_file, 'w') as f:
            f.write("# Entity Relationship Diagram\n\n")
            f.write("```mermaid\n")
            f.write(state['erd_diagram'])
            f.write("\n```\n")
        print(f"📊 ERD (Markdown) saved to: {erd_md_file}")


def run_rdbms_builder(
    requirements: str,
    dialect: str = "postgresql",
    interactive: bool = True
) -> dict:
    """
    Run the RDBMS builder with the given requirements.
    
    Args:
        requirements: Natural language requirements
        dialect: SQL dialect (postgresql, mysql, sqlite)
        interactive: Whether to ask clarifying questions interactively
    """
    print("=" * 60)
    print("🚀 RDBMS Builder Starting...")
    print(f"📝 Target dialect: {dialect.upper()}")
    print("=" * 60)
    print(f"\n📋 Requirements:\n{requirements}\n")
    print("=" * 60)
    
    # Phase 1: Check for clarification needs
    initial_state = get_initial_state(requirements, dialect)
    state = graph.invoke(initial_state)
    
    # Handle clarification if needed
    if state.get('needs_clarification') and state.get('clarifying_questions'):
        print_questions(state['clarifying_questions'])
        
        if interactive:
            answers = get_user_answers(state['clarifying_questions'])
            
            if answers:
                # Update requirements with answers and continue
                enriched_requirements = requirements + "\n\nAdditional clarifications:\n" + "\n".join(answers)
                state = get_initial_state(enriched_requirements, dialect, answers)
                state = graph_after_clarification.invoke(state)
            else:
                print("\n⚠️ No answers provided, proceeding with original requirements...")
                state = get_initial_state(requirements, dialect)
                state['needs_clarification'] = False
                state = graph_after_clarification.invoke(state)
        else:
            print("\n⚠️ Non-interactive mode, proceeding with original requirements...")
            state = get_initial_state(requirements, dialect)
            state = graph_after_clarification.invoke(state)
    
    print("\n" + "=" * 60)
    print("🎉 RDBMS Builder Complete!")
    print("=" * 60)
    
    return state


def main():
    # Example: Fleet Management System
    requirements = """
    I want to build a fleet management system where:
    - Companies can register and manage their vehicle fleet
    - Each company has multiple vehicles (cars, trucks, motorcycles)
    - Drivers are assigned to vehicles, one driver per vehicle at a time
    - We need to track maintenance schedules for each vehicle
    - Record fuel consumption logs with date, amount, and cost
    - Track vehicle locations with GPS coordinates
    - Managers can generate reports on fleet performance
    """
    
    # Ask user for dialect
    print("\n🔧 Configuration")
    print("-" * 40)
    print("Available SQL dialects:")
    print("  1. PostgreSQL (default)")
    print("  2. MySQL")
    print("  3. SQLite")
    
    dialect_choice = input("\nSelect dialect [1-3] (or press Enter for PostgreSQL): ").strip()
    
    dialect_map = {"1": "postgresql", "2": "mysql", "3": "sqlite", "": "postgresql"}
    dialect = dialect_map.get(dialect_choice, "postgresql")
    
    # Run the builder
    result = run_rdbms_builder(requirements, dialect=dialect, interactive=True)
    
    # Print results
    print("\n" + "=" * 60)
    print("📄 Generated DDL Script:")
    print("=" * 60)
    print(result['ddl_script'])
    
    if result.get('erd_diagram'):
        print("\n" + "=" * 60)
        print("📊 ERD Diagram (Mermaid):")
        print("=" * 60)
        print(result['erd_diagram'])
    
    # Save outputs
    print("\n" + "-" * 60)
    save_choice = input("💾 Save outputs to files? [Y/n]: ").strip().lower()
    if save_choice != 'n':
        save_outputs(result)
    
    # Print any remaining issues
    if result.get('validation_issues'):
        print("\n⚠️  Remaining Issues:")
        for issue in result['validation_issues']:
            print(f"   - {issue}")


def generate_all_dialects(requirements: str) -> dict:
    """
    Generate schemas for all supported dialects.
    Useful for projects that need to support multiple databases.
    """
    results = {}
    
    for dialect in ["postgresql", "mysql", "sqlite"]:
        print(f"\n{'='*60}")
        print(f"Generating for {dialect.upper()}...")
        print('='*60)
        
        result = run_rdbms_builder(requirements, dialect=dialect, interactive=False)
        results[dialect] = result
    
    return results


if __name__ == "__main__":
    main()