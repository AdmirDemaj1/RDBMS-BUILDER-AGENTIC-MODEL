# main.py
from graph.builder import graph, graph_continue
from graph.state import GraphState, TaskStatus
from utils.state_manager import StateManager
from utils.task_manager import print_task_summary
import os


def print_header():
    print("\n" + "=" * 60)
    print("🏗️  RDBMS BUILDER (Optimized)")
    print("=" * 60)


def print_questions(questions: list) -> None:
    print("\n" + "=" * 50)
    print("❓ CLARIFICATION NEEDED")
    print("=" * 50)
    for i, q in enumerate(questions, 1):
        print(f"\n{i}. {q['question']}")
        if q.get("options"):
            print(f"   Options: {', '.join(q['options'])}")
    print("=" * 50)


def get_user_answers(questions: list) -> list:
    answers = []
    print("\nAnswer questions (Enter to skip):\n")
    for i, q in enumerate(questions, 1):
        answer = input(f"Q{i}: ").strip()
        if answer:
            answers.append(f"Q: {q['question']} A: {answer}")
    return answers


def save_outputs(state: GraphState, output_dir: str = "output") -> None:
    os.makedirs(output_dir, exist_ok=True)
    archive = state["archive"]
    working = state["working"]
    
    if archive.get("ddl_script"):
        dialect = working.get("sql_dialect", "postgresql")
        path = os.path.join(output_dir, f"schema_{dialect}.sql")
        with open(path, "w") as f:
            f.write(archive["ddl_script"])
        print(f"📄 DDL: {path}")
    
    if archive.get("erd_diagram"):
        path = os.path.join(output_dir, "erd.md")
        with open(path, "w") as f:
            f.write("# ERD\n\n```mermaid\n")
            f.write(archive["erd_diagram"])
            f.write("\n```\n")
        print(f"📊 ERD: {path}")
    
    # Task report
    path = os.path.join(output_dir, "report.txt")
    with open(path, "w") as f:
        f.write("RDBMS Builder Report\n")
        f.write("=" * 40 + "\n\n")
        for task in archive["tasks"]:
            f.write(f"[{task['status']}] {task['content']}\n")
            if task.get("result"):
                f.write(f"  Result: {task['result']}\n")
        f.write(f"\nLLM Calls: {archive['total_llm_calls']}\n")
    print(f"📋 Report: {path}")


def print_critic_summary(state: GraphState) -> None:
    reports = state["archive"].get("critic_reports", [])
    if not reports:
        return
    
    print("\n" + "=" * 50)
    print("🔍 CRITIC SUMMARY")
    print("=" * 50)
    for i, r in enumerate(reports, 1):
        items = len(r.get("feedback_items", []))
        print(f"  #{i}: Score {r['overall_score']}/10 ({items} items)")
    print("=" * 50)


def run_builder(
    requirements: str,
    dialect: str = "postgresql",
    enable_critic: bool = True,
    interactive: bool = True
) -> GraphState:
    
    print_header()
    print(f"📝 Dialect: {dialect.upper()}")
    print(f"🔍 Critic: {'On' if enable_critic else 'Off'}")
    print("=" * 60)
    
    state = StateManager.create_initial_state(requirements, dialect, enable_critic)
    state = graph.invoke(state)
    
    # Handle clarification
    if state["working"].get("needs_clarification"):
        questions = state["archive"].get("clarifying_questions", [])
        if questions:
            print_questions(questions)
            
            if interactive:
                answers = get_user_answers(questions)
                if answers:
                    StateManager.add_user_answers(state, answers)
                state["working"]["needs_clarification"] = False
                state = graph_continue.invoke(state)
            else:
                state["working"]["needs_clarification"] = False
                state = graph_continue.invoke(state)
    
    print_task_summary(state)
    print_critic_summary(state)
    
    print("\n" + "=" * 60)
    print("🎉 COMPLETE!")
    print(f"📊 LLM Calls: {state['archive']['total_llm_calls']}")
    print("=" * 60)
    
    return state


def main():
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
    
    print("\n🔧 Configuration")
    print("-" * 40)
    
    d = input("Dialect [1=PostgreSQL, 2=MySQL, 3=SQLite]: ").strip()
    dialect = {"1": "postgresql", "2": "mysql", "3": "sqlite", "": "postgresql"}.get(d, "postgresql")
    
    c = input("Enable critic? [Y/n]: ").strip().lower()
    enable_critic = c != "n"
    
    result = run_builder(requirements, dialect, enable_critic)
    
    # Show DDL
    print("\n" + "=" * 60)
    print("📄 DDL SCRIPT")
    print("=" * 60)
    ddl = result["archive"].get("ddl_script", "")
    if len(ddl) > 3000:
        print(ddl[:3000] + "\n... (truncated)")
    else:
        print(ddl)
    
    # Show ERD
    if result["archive"].get("erd_diagram"):
        print("\n" + "=" * 60)
        print("📊 ERD")
        print("=" * 60)
        print(result["archive"]["erd_diagram"])
    
    # Save
    s = input("\n💾 Save outputs? [Y/n]: ").strip().lower()
    if s != "n":
        save_outputs(result)


if __name__ == "__main__":
    main()