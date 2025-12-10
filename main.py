# main.py
from graph.builder import graph, graph_continue
from graph.state import GraphState, TaskStatus
from utils.task_manager import print_task_summary, get_default_tasks
from typing import Any, Optional
import os


def get_initial_state(
    requirements: str,
    dialect: str = "postgresql",
    enable_critic: bool = True,
    user_answers: Optional[list] = None,
    existing_tasks: Optional[list] = None
) -> GraphState:
    """Create initial state for the graph."""
    return {
        "user_requirements": requirements,
        "user_answers": user_answers or [],
        "sql_dialect": dialect,
        "enable_critic": enable_critic,
        "tasks": existing_tasks or [],
        "current_task_id": None,
        "clarifying_questions": [],
        "needs_clarification": False,
        "entities": [],
        "relationships": [],
        "tables": [],
        "critic_reports": [],
        "critic_revision_count": 0,
        "max_critic_revisions": 2,
        "validation_issues": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "ddl_script": "",
        "erd_diagram": "",
        "current_step": "start",
        "is_complete": False,
        "error": None
    }


def print_header():
    """Print the application header."""
    print("\n" + "=" * 60)
    print("🏗️  RDBMS BUILDER WITH CRITIC AGENT")
    print("=" * 60)


def print_questions(questions: list) -> None:
    """Print clarifying questions."""
    print("\n" + "=" * 60)
    print("❓ CLARIFICATION NEEDED")
    print("=" * 60)
    
    for i, q in enumerate[Any](questions, 1):
        print(f"\n{i}. {q['question']}")
        print(f"   Why: {q['context']}")
        if q.get('options'):
            print(f"   Suggestions: {', '.join(q['options'])}")
    
    print("\n" + "=" * 60)


def get_user_answers(questions: list) -> list:
    """Interactively get answers from user."""
    answers = []
    print("\nPlease answer (press Enter to skip):\n")
    
    for i, q in enumerate(questions, 1):
        print(f"Q{i}: {q['question']}")
        if q.get('options'):
            print(f"    Options: {', '.join(q['options'])}")
        
        answer = input(f"A{i}: ").strip()
        if answer:
            answers.append(f"Q: {q['question']} A: {answer}")
    
    return answers


def print_critic_summary(critic_reports: list) -> None:
    """Print a summary of critic evaluations."""
    if not critic_reports:
        return
    
    print("\n" + "=" * 60)
    print("🔍 CRITIC EVALUATION SUMMARY")
    print("=" * 60)
    
    for i, report in enumerate(critic_reports, 1):
        print(f"\n📊 Evaluation #{i}:")
        print(f"   Score: {report['overall_score']}/10")
        print(f"   Summary: {report['summary']}")
        
        feedback = report.get('feedback_items', [])
        if feedback:
            applied = sum(1 for f in feedback if f.get('applied'))
            print(f"   Feedback: {len(feedback)} items ({applied} addressed)")
    
    print("=" * 60)


def save_outputs(state: GraphState, output_dir: str = "output") -> None:
    """Save generated outputs to files."""
    os.makedirs(output_dir, exist_ok=True)
    
    dialect = state.get('sql_dialect', 'postgresql')
    
    # Save DDL
    if state.get('ddl_script'):
        ddl_file = os.path.join(output_dir, f"schema_{dialect}.sql")
        with open(ddl_file, 'w') as f:
            f.write(state['ddl_script'])
        print(f"📄 DDL saved: {ddl_file}")
    
    # Save ERD
    if state.get('erd_diagram'):
        erd_file = os.path.join(output_dir, "erd_diagram.mmd")
        with open(erd_file, 'w') as f:
            f.write(state['erd_diagram'])
        print(f"📊 ERD saved: {erd_file}")
        
        # Markdown version
        erd_md_file = os.path.join(output_dir, "erd_diagram.md")
        with open(erd_md_file, 'w') as f:
            f.write("# Entity Relationship Diagram\n\n")
            f.write("```mermaid\n")
            f.write(state['erd_diagram'])
            f.write("\n```\n")
        print(f"📊 ERD (MD) saved: {erd_md_file}")
    
    # Save task report
    if state.get('tasks'):
        report_file = os.path.join(output_dir, "task_report.txt")
        with open(report_file, 'w') as f:
            f.write("RDBMS Builder - Task Execution Report\n")
            f.write("=" * 50 + "\n\n")
            
            for i, task in enumerate(state['tasks'], 1):
                status_icon = {
                    TaskStatus.COMPLETED: "✅",
                    TaskStatus.FAILED: "❌",
                    TaskStatus.PENDING: "⏳",
                    TaskStatus.IN_PROGRESS: "🔄",
                    TaskStatus.SKIPPED: "⏭️"
                }.get(task['status'], "❓")
                
                f.write(f"{i}. {status_icon} {task['content']}\n")
                f.write(f"   Status: {task['status']}\n")
                if task.get('result'):
                    f.write(f"   Result: {task['result']}\n")
                if task.get('error'):
                    f.write(f"   Error: {task['error']}\n")
                f.write("\n")
        
        print(f"📋 Task report saved: {report_file}")
    
    # Save critic report
    if state.get('critic_reports'):
        critic_file = os.path.join(output_dir, "critic_report.txt")
        with open(critic_file, 'w') as f:
            f.write("RDBMS Builder - Critic Evaluation Report\n")
            f.write("=" * 50 + "\n\n")
            
            for i, report in enumerate(state['critic_reports'], 1):
                f.write(f"Evaluation #{i}\n")
                f.write("-" * 30 + "\n")
                f.write(f"Score: {report['overall_score']}/10\n")
                f.write(f"Summary: {report['summary']}\n")
                f.write(f"Required Revision: {report['requires_revision']}\n\n")
                
                f.write("Feedback Items:\n")
                for item in report.get('feedback_items', []):
                    status = "✅" if item.get('applied') else "⏳"
                    f.write(f"  {status} [{item['severity'].upper()}] {item['target']}\n")
                    f.write(f"     Issue: {item['issue']}\n")
                    f.write(f"     Recommendation: {item['recommendation']}\n\n")
                
                f.write("\n")
        
        print(f"🔍 Critic report saved: {critic_file}")


def run_rdbms_builder(
    requirements: str,
    dialect: str = "postgresql",
    enable_critic: bool = True,
    interactive: bool = True
) -> dict:
    """Run the RDBMS builder with critic agent."""
    
    print_header()
    print(f"📝 Target dialect: {dialect.upper()}")
    print(f"🔍 Critic agent: {'Enabled' if enable_critic else 'Disabled'}")
    print("=" * 60)
    print(f"\n📋 Requirements:\n{requirements}\n")
    print("=" * 60)
    
    # Phase 1: Run planner and check for clarification
    initial_state = get_initial_state(requirements, dialect, enable_critic)
    state = graph.invoke(initial_state)
    
    # Handle clarification if needed
    if state.get('needs_clarification') and state.get('clarifying_questions'):
        print_questions(state['clarifying_questions'])
        
        if interactive:
            answers = get_user_answers(state['clarifying_questions'])
            
            if answers:
                enriched = requirements + "\n\nClarifications:\n" + "\n".join(answers)
                
                tasks = state['tasks']
                
                continue_state = get_initial_state(
                    enriched, 
                    dialect,
                    enable_critic,
                    answers,
                    tasks
                )
                continue_state['needs_clarification'] = False
                
                state = graph_continue.invoke(continue_state)
            else:
                print("\n⚠️ No answers provided, proceeding...")
                continue_state = state.copy()
                continue_state['needs_clarification'] = False
                state = graph_continue.invoke(continue_state)
        else:
            print("\n⚠️ Non-interactive mode, proceeding...")
            continue_state = state.copy()
            continue_state['needs_clarification'] = False
            state = graph_continue.invoke(continue_state)
    
    # Print summaries
    if state.get('tasks'):
        print_task_summary(state['tasks'])
    
    if state.get('critic_reports'):
        print_critic_summary(state['critic_reports'])
    
    print("\n" + "=" * 60)
    print("🎉 RDBMS BUILDER COMPLETE!")
    print("=" * 60)
    
    return state


def main():
    """Main entry point."""
    
    # Example requirements
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
    
    # Configuration
    print("\n🔧 Configuration")
    print("-" * 40)
    
    # Dialect selection
    print("SQL Dialects:")
    print("  1. PostgreSQL (default)")
    print("  2. MySQL")
    print("  3. SQLite")
    
    dialect_choice = input("\nSelect dialect [1-3]: ").strip()
    dialect_map = {"1": "postgresql", "2": "mysql", "3": "sqlite", "": "postgresql"}
    dialect = dialect_map.get(dialect_choice, "postgresql")
    
    # Critic toggle
    critic_choice = input("Enable critic agent? [Y/n]: ").strip().lower()
    enable_critic = critic_choice != 'n'
    
    # Run builder
    result = run_rdbms_builder(
        requirements, 
        dialect=dialect, 
        enable_critic=enable_critic,
        interactive=True
    )
    
    # Display results
    print("\n" + "=" * 60)
    print("📄 GENERATED DDL SCRIPT")
    print("=" * 60)
    print(result['ddl_script'])
    
    if result.get('erd_diagram'):
        print("\n" + "=" * 60)
        print("📊 ERD DIAGRAM (Mermaid)")
        print("=" * 60)
        print(result['erd_diagram'])
    
    # Save option
    print("\n" + "-" * 60)
    save_choice = input("💾 Save outputs? [Y/n]: ").strip().lower()
    if save_choice != 'n':
        save_outputs(result)
    
    # Show any issues
    if result.get('validation_issues'):
        print("\n⚠️ Remaining Validation Issues:")
        for issue in result['validation_issues']:
            print(f"   - {issue}")


if __name__ == "__main__":
    main()