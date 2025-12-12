# main.py
from graph.builder import graph, graph_continue
from graph.state import GraphState, TaskStatus
from utils.state_manager import StateManager
from utils.task_manager import print_task_summary
from utils.thread_manager import ThreadManager, create_thread_config, get_or_create_thread_id
import os
from typing import Optional


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
    
    # NestJS Architecture
    if archive.get("nestjs_architecture"):
        save_nestjs_architecture(archive["nestjs_architecture"], output_dir)
    
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


def save_nestjs_architecture(architecture: dict, output_dir: str) -> None:
    """Save NestJS architecture documentation files."""
    nestjs_dir = os.path.join(output_dir, "nestjs")
    os.makedirs(nestjs_dir, exist_ok=True)
    
    # Save comprehensive architecture documentation
    arch_path = os.path.join(nestjs_dir, "ARCHITECTURE.md")
    with open(arch_path, "w") as f:
        f.write(f"# {architecture.get('project_name', 'NestJS Backend')} - Architecture Blueprint\n\n")
        
        if architecture.get("description"):
            f.write(f"> {architecture['description']}\n\n")
        
        f.write("---\n\n")
        
        # Table of Contents
        f.write("## Table of Contents\n\n")
        f.write("1. [Directory Structure](#directory-structure)\n")
        f.write("2. [Module Architecture](#module-architecture)\n")
        f.write("3. [API Endpoints](#api-endpoints)\n")
        f.write("4. [Data Flows](#data-flows)\n")
        f.write("5. [Event-Driven Architecture](#event-driven-architecture)\n")
        f.write("6. [Security](#security)\n")
        f.write("7. [Configuration](#configuration)\n\n")
        f.write("---\n\n")
        
        # Directory Structure
        f.write("## Directory Structure\n\n")
        f.write("```\n")
        f.write(architecture.get("directory_structure", ""))
        f.write("\n```\n\n")
        
        # Module Architecture Diagram
        f.write("## Module Architecture\n\n")
        if architecture.get("module_diagram"):
            f.write("```mermaid\n")
            f.write(architecture["module_diagram"])
            f.write("\n```\n\n")
        
        # Modules Detail
        f.write("### Modules Overview\n\n")
        for module in architecture.get("modules", []):
            f.write(f"#### {module['name']}Module\n\n")
            if module.get("description"):
                f.write(f"{module['description']}\n\n")
            f.write(f"- **Entities**: {', '.join(module.get('entities', []))}\n")
            f.write(f"- **Components**: Controller, Service, Repository\n")
            if module.get("dependencies"):
                f.write(f"- **Dependencies**: {', '.join(module['dependencies'])}\n")
            f.write("\n")
        
        # API Endpoints
        f.write("## API Endpoints\n\n")
        if architecture.get("endpoint_table"):
            f.write(architecture["endpoint_table"])
        else:
            f.write("| Method | Path | Description |\n")
            f.write("|--------|------|-------------|\n")
            for endpoint in architecture.get("endpoints", []):
                f.write(f"| {endpoint['method']} | `{endpoint['path']}` | {endpoint['description']} |\n")
        f.write("\n\n")
        
        # Data Flows
        f.write("## Data Flows\n\n")
        f.write("These diagrams show how requests flow through the application.\n\n")
        
        flow_diagrams = architecture.get("flow_diagrams", {})
        data_flows = architecture.get("data_flows", [])
        
        for flow in data_flows:
            f.write(f"### {flow['name']}\n\n")
            f.write(f"**Trigger**: `{flow['trigger']}`\n\n")
            
            if flow['name'] in flow_diagrams:
                f.write("```mermaid\n")
                f.write(flow_diagrams[flow['name']])
                f.write("\n```\n\n")
            
            f.write("**Steps**:\n\n")
            for step in flow.get("steps", []):
                f.write(f"{step['step']}. **{step['component']}**: {step['action']}\n")
            f.write("\n")
        
        # Event-Driven Architecture
        f.write("## Event-Driven Architecture\n\n")
        
        event_patterns = architecture.get("event_patterns", [])
        message_queue = architecture.get("message_queue")
        
        if event_patterns:
            if message_queue:
                f.write(f"**Message Queue**: {message_queue}\n\n")
            
            f.write("### Event Patterns\n\n")
            f.write("This system uses event-driven architecture for asynchronous processing and real-time updates.\n\n")
            
            for event in event_patterns:
                f.write(f"#### `{event['event_name']}`\n\n")
                f.write(f"- **Trigger**: {event['trigger']}\n")
                f.write(f"- **Purpose**: {event['purpose']}\n")
                f.write(f"- **Consumers**: {', '.join(event['consumers'])}\n\n")
            
            f.write("### Implementation Guide\n\n")
            f.write("1. Install event emitter: `npm install @nestjs/event-emitter`\n")
            if message_queue:
                if "RabbitMQ" in message_queue:
                    f.write("2. Install message queue: `npm install @nestjs/microservices amqplib`\n")
                elif "Redis" in message_queue:
                    f.write("2. Install message queue: `npm install @nestjs/microservices ioredis`\n")
                elif "AWS" in message_queue:
                    f.write("2. Install message queue: `npm install @nestjs/microservices aws-sdk`\n")
            f.write("3. Import EventEmitterModule in AppModule\n")
            f.write("4. Emit events: `this.eventEmitter.emit('event.name', payload)`\n")
            f.write("5. Listen with decorators: `@OnEvent('event.name')`\n\n")
        else:
            f.write("**Event-driven architecture is not required** for this system based on the current requirements.\n\n")
            f.write("Consider adding events if you need:\n")
            f.write("- Real-time notifications\n")
            f.write("- Async background processing\n")
            f.write("- Webhooks or external integrations\n")
            f.write("- Audit logging\n")
            f.write("- Cache invalidation patterns\n\n")
        
        # Security
        f.write("## Security\n\n")
        
        f.write("### Guards\n\n")
        guards_detail = architecture.get("guards_detail", [])
        if guards_detail:
            for guard in guards_detail:
                f.write(f"#### {guard['name']}\n")
                f.write(f"- **Purpose**: {guard['purpose']}\n")
                f.write(f"- **Applies to**: {', '.join(guard['applies_to'])}\n\n")
        else:
            for guard in architecture.get("guards", []):
                f.write(f"- {guard}\n")
            f.write("\n")
        
        f.write("### Interceptors\n\n")
        interceptors_detail = architecture.get("interceptors_detail", [])
        if interceptors_detail:
            for interceptor in interceptors_detail:
                f.write(f"#### {interceptor['name']}\n")
                f.write(f"- **Purpose**: {interceptor['purpose']}\n")
                f.write(f"- **Applies to**: {', '.join(interceptor['applies_to'])}\n\n")
        else:
            for interceptor in architecture.get("interceptors", []):
                f.write(f"- {interceptor}\n")
            f.write("\n")
        
        pipes = architecture.get("pipes", [])
        if pipes:
            f.write("### Pipes\n\n")
            for pipe in pipes:
                f.write(f"- **{pipe['name']}**: {pipe['purpose']}\n")
            f.write("\n")
        
        middlewares = architecture.get("middlewares", [])
        if middlewares:
            f.write("### Middlewares\n\n")
            for mw in middlewares:
                f.write(f"#### {mw['name']}\n")
                f.write(f"- **Purpose**: {mw['purpose']}\n")
                f.write(f"- **Routes**: {', '.join(mw['routes'])}\n\n")
        
        # Configuration
        f.write("## Configuration\n\n")
        
        env_vars = architecture.get("environment_variables", [])
        if env_vars:
            f.write("### Environment Variables\n\n")
            f.write("```env\n")
            for var in env_vars:
                f.write(f"{var}=\n")
            f.write("```\n\n")
        
        integrations = architecture.get("external_integrations", [])
        if integrations:
            f.write("### External Integrations\n\n")
            for integration in integrations:
                f.write(f"- {integration}\n")
            f.write("\n")
    
    print(f"📋 NestJS Architecture: {arch_path}")
    
    # Save endpoint documentation separately
    endpoints_path = os.path.join(nestjs_dir, "API_ENDPOINTS.md")
    with open(endpoints_path, "w") as f:
        f.write("# API Endpoints Documentation\n\n")
        
        # Group endpoints by module/resource
        endpoints = architecture.get("endpoints", [])
        if endpoints:
            current_resource = ""
            for ep in endpoints:
                # Extract resource from path
                parts = ep['path'].split('/')
                resource = parts[2] if len(parts) > 2 else "root"
                
                if resource != current_resource:
                    current_resource = resource
                    f.write(f"\n## {resource.replace('-', ' ').title()}\n\n")
                
                f.write(f"### {ep['method']} `{ep['path']}`\n\n")
                f.write(f"{ep['description']}\n\n")
                if ep.get("request_dto"):
                    f.write(f"**Request Body**: {ep['request_dto']}\n\n")
                if ep.get("response_dto"):
                    f.write(f"**Response**: {ep['response_dto']}\n\n")
                f.write("---\n\n")
    
    print(f"📡 API Endpoints: {endpoints_path}")


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


def get_thread_history(thread_id: str, project_name: Optional[str] = None) -> None:
    """
    Display the history of a specific thread from LangSmith.
    
    Args:
        thread_id: The thread ID to query.
        project_name: Optional LangSmith project name.
    """
    print("\n" + "=" * 60)
    print(f"🧵 THREAD HISTORY: {thread_id[:8]}...")
    print("=" * 60)
    
    try:
        runs = ThreadManager.get_thread_history(
            thread_id=thread_id,
            project_name=project_name
        )
        
        if not runs:
            print("No runs found for this thread.")
            return
        
        for i, run in enumerate(runs, 1):
            status_icon = "✅" if run["status"] == "success" else "❌"
            print(f"\n{i}. {status_icon} {run['name']}")
            print(f"   Type: {run['run_type']}")
            print(f"   Started: {run['start_time']}")
            if run.get("error"):
                print(f"   Error: {run['error']}")
        
        print("\n" + "=" * 60)
    except Exception as e:
        print(f"Error fetching thread history: {e}")


def list_recent_threads(project_name: Optional[str] = None, limit: int = 10) -> None:
    """
    List recent threads from LangSmith.
    
    Args:
        project_name: Optional LangSmith project name.
        limit: Maximum number of threads to display.
    """
    print("\n" + "=" * 60)
    print("🧵 RECENT THREADS")
    print("=" * 60)
    
    try:
        threads = ThreadManager.list_threads(
            project_name=project_name,
            limit=limit
        )
        
        if not threads:
            print("No threads found.")
            return
        
        for i, thread in enumerate(threads, 1):
            print(f"\n{i}. Thread: {thread['thread_id'][:8]}...")
            print(f"   Runs: {thread['run_count']}")
            print(f"   Last Activity: {thread['last_activity']}")
        
        print("\n" + "=" * 60)
    except Exception as e:
        print(f"Error fetching threads: {e}")


def run_builder(
    requirements: str,
    dialect: str = "postgresql",
    enable_critic: bool = True,
    generate_nestjs: bool = True,
    interactive: bool = True,
    thread_id: Optional[str] = None,
    project_name: Optional[str] = None
) -> GraphState:
    """
    Run the RDBMS builder pipeline.
    
    Args:
        requirements: User requirements for the database schema.
        dialect: SQL dialect (postgresql, mysql, sqlite).
        enable_critic: Whether to enable the critic node for schema review.
        generate_nestjs: Whether to generate NestJS backend architecture.
        interactive: Whether to prompt for user input during clarification.
        thread_id: Optional thread ID for LangSmith conversation tracking.
                  If not provided, a new UUID will be generated.
        project_name: Optional LangSmith project name for tracing.
    
    Returns:
        Final GraphState with all generated artifacts.
    """
    print_header()
    print(f"📝 Dialect: {dialect.upper()}")
    print(f"🔍 Critic: {'On' if enable_critic else 'Off'}")
    print(f"🚀 NestJS: {'On' if generate_nestjs else 'Off'}")
    
    # Initialize thread tracking
    thread_id = get_or_create_thread_id(thread_id)
    print(f"🧵 Thread: {thread_id[:8]}...")
    print("=" * 60)
    
    # Create state with thread ID
    state = StateManager.create_initial_state(
        requirements, dialect, enable_critic, generate_nestjs, thread_id
    )
    
    # Create LangSmith config with thread metadata
    config = create_thread_config(
        thread_id=thread_id,
        project_name=project_name,
        run_name="RDBMS Builder - Initial",
        tags=["rdbms-builder", dialect]
    )
    
    # Invoke graph with thread tracking
    state = graph.invoke(state, config=config)
    
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
                
                # Continue with same thread
                continue_config = create_thread_config(
                    thread_id=thread_id,
                    project_name=project_name,
                    run_name="RDBMS Builder - Continue",
                    tags=["rdbms-builder", dialect, "continuation"]
                )
                state = graph_continue.invoke(state, config=continue_config)
            else:
                state["working"]["needs_clarification"] = False
                continue_config = create_thread_config(
                    thread_id=thread_id,
                    project_name=project_name,
                    run_name="RDBMS Builder - Continue (Auto)",
                    tags=["rdbms-builder", dialect, "continuation"]
                )
                state = graph_continue.invoke(state, config=continue_config)
    
    print_task_summary(state)
    print_critic_summary(state)
    
    print("\n" + "=" * 60)
    print("🎉 COMPLETE!")
    print(f"📊 LLM Calls: {state['archive']['total_llm_calls']}")
    print(f"🧵 Thread ID: {thread_id}")
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
    
    n = input("Generate NestJS backend? [Y/n]: ").strip().lower()
    generate_nestjs = n != "n"
    
    result = run_builder(requirements, dialect, enable_critic, generate_nestjs)
    
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
    
    # Show NestJS Architecture Summary
    if result["archive"].get("nestjs_architecture"):
        print("\n" + "=" * 60)
        print("🚀 NESTJS ARCHITECTURE")
        print("=" * 60)
        arch = result["archive"]["nestjs_architecture"]
        print(f"Project: {arch.get('project_name', 'N/A')}")
        print(f"Modules: {len(arch.get('modules', []))}")
        print(f"Entities: {len(arch.get('entities', []))}")
        print(f"Endpoints: {len(arch.get('endpoints', []))}")
        print("\nDirectory Structure:")
        print(arch.get("directory_structure", "")[:500])
        if len(arch.get("directory_structure", "")) > 500:
            print("... (truncated)")
    
    # Save
    s = input("\n💾 Save outputs? [Y/n]: ").strip().lower()
    if s != "n":
        save_outputs(result)


if __name__ == "__main__":
    main()