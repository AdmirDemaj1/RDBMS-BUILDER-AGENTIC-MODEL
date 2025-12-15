# main.py
from builder.graph.builder import graph, graph_continue, get_compiled_graphs
from builder.graph.state import GraphState, TaskStatus
from builder.utils.state_manager import StateManager
from builder.utils.task_manager import print_task_summary
from builder.utils.thread_manager import ThreadManager, create_thread_config, get_or_create_thread_id
from builder.utils.checkpoint_manager import (
    CheckpointManager,
    CheckpointerType,
    create_checkpoint_manager_from_env
)
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


def list_checkpoints(
    thread_id: str,
    checkpoint_type: CheckpointerType = CheckpointerType.SQLITE,
    connection_string: Optional[str] = None,
    limit: int = 10
) -> None:
    """
    List checkpoints for a specific thread.
    
    Args:
        thread_id: The thread ID to query.
        checkpoint_type: Type of checkpointer (memory, sqlite, postgres).
        connection_string: Optional connection string for the checkpointer.
        limit: Maximum number of checkpoints to display.
    """
    print("\n" + "=" * 60)
    print(f"💾 CHECKPOINTS FOR THREAD: {thread_id[:8]}...")
    print("=" * 60)
    
    try:
        checkpoint_manager = CheckpointManager(
            checkpointer_type=checkpoint_type,
            connection_string=connection_string
        )
        
        checkpoints = checkpoint_manager.list_checkpoints(thread_id, limit=limit)
        
        if not checkpoints:
            print("No checkpoints found for this thread.")
            return
        
        for i, cp in enumerate(checkpoints, 1):
            print(f"\n{i}. Checkpoint ID: {cp.get('checkpoint_id', 'N/A')[:8]}...")
            if cp.get('parent_checkpoint_id'):
                print(f"   Parent: {cp['parent_checkpoint_id'][:8]}...")
            if cp.get('created_at'):
                print(f"   Created: {cp['created_at']}")
            if cp.get('metadata'):
                print(f"   Metadata: {cp['metadata']}")
        
        print("\n" + "=" * 60)
    except Exception as e:
        print(f"Error fetching checkpoints: {e}")


def resume_from_checkpoint(
    thread_id: str,
    checkpoint_id: Optional[str] = None,
    checkpoint_type: CheckpointerType = CheckpointerType.SQLITE,
    connection_string: Optional[str] = None,
    project_name: Optional[str] = None
) -> Optional[GraphState]:
    """
    Resume execution from a specific checkpoint.
    
    Args:
        thread_id: The thread ID to resume.
        checkpoint_id: Optional specific checkpoint ID (if None, uses latest).
        checkpoint_type: Type of checkpointer.
        connection_string: Optional connection string.
        project_name: Optional LangSmith project name.
    
    Returns:
        GraphState at the checkpoint, or None if not found.
    """
    print("\n" + "=" * 60)
    print(f"🔄 RESUMING FROM CHECKPOINT")
    print(f"Thread: {thread_id[:8]}...")
    if checkpoint_id:
        print(f"Checkpoint: {checkpoint_id[:8]}...")
    print("=" * 60)
    
    try:
        checkpoint_manager = CheckpointManager(
            checkpointer_type=checkpoint_type,
            connection_string=connection_string
        )
        
        # Get state at checkpoint
        state = checkpoint_manager.get_state(thread_id, checkpoint_id)
        
        if not state:
            print("❌ No state found at checkpoint.")
            return None
        
        print("✅ State retrieved successfully!")
        
        # Display state summary
        if "working" in state:
            working = state["working"]
            print(f"\nCurrent Step: {working.get('current_step', 'N/A')}")
            print(f"Entities: {len(working.get('entities', []))}")
            print(f"Tables: {len(working.get('tables', []))}")
            print(f"Is Complete: {working.get('is_complete', False)}")
        
        return state
    
    except Exception as e:
        print(f"❌ Error resuming from checkpoint: {e}")
        return None


def run_builder(
    requirements: str,
    dialect: Optional[str] = None,
    enable_critic: Optional[bool] = None,
    generate_nestjs: Optional[bool] = None,
    interactive: bool = True,
    thread_id: Optional[str] = None,
    project_name: Optional[str] = None,
    enable_checkpointing: bool = True,
    checkpoint_type: CheckpointerType = CheckpointerType.SQLITE,
    checkpoint_connection: Optional[str] = None
) -> GraphState:
    """
    Run the RDBMS builder pipeline with long-term memory checkpointing.
    
    Args:
        requirements: User requirements for the database schema.
        dialect: SQL dialect (postgresql, mysql, sqlite). If None and interactive, prompts user.
        enable_critic: Whether to enable the critic node for schema review. If None and interactive, prompts user.
        generate_nestjs: Whether to generate NestJS backend architecture. If None and interactive, prompts user.
        interactive: Whether to prompt for user input during clarification and configuration.
        thread_id: Optional thread ID for LangSmith conversation tracking.
                  If not provided, a new UUID will be generated.
        project_name: Optional LangSmith project name for tracing.
        enable_checkpointing: Whether to enable long-term memory checkpointing (default: True).
        checkpoint_type: Type of checkpointer to use (memory, sqlite, postgres).
        checkpoint_connection: Optional connection string for checkpointer.
    
    Returns:
        Final GraphState with all generated artifacts.
    """
    print_header()
    
    # Prompt for configuration if interactive and not provided
    if interactive:
        if dialect is None:
            d = input("Dialect [1=PostgreSQL (default), 2=MySQL, 3=SQLite]: ").strip()
            dialect = {"1": "postgresql", "2": "mysql", "3": "sqlite", "": "postgresql"}.get(d, "postgresql")
        
        if enable_critic is None:
            c = input("Enable critic (schema review)? [Y/n]: ").strip().lower()
            enable_critic = c != "n"
        
        if generate_nestjs is None:
            n = input("Generate NestJS backend? [Y/n]: ").strip().lower()
            generate_nestjs = n != "n"
    
    # Apply defaults for non-interactive mode
    dialect = dialect or "postgresql"
    enable_critic = enable_critic if enable_critic is not None else True
    generate_nestjs = generate_nestjs if generate_nestjs is not None else True
    
    print(f"📝 Dialect: {dialect.upper()}")
    print(f"🔍 Critic: {'On' if enable_critic else 'Off'}")
    print(f"🚀 NestJS: {'On' if generate_nestjs else 'Off'}")
    print(f"💾 Checkpointing: {'On' if enable_checkpointing else 'Off'} ({checkpoint_type.value if enable_checkpointing else 'N/A'})")
    
    # Initialize thread tracking
    thread_id = get_or_create_thread_id(thread_id)
    print(f"🧵 Thread: {thread_id[:8]}...")
    print("=" * 60)
    
    # Create state with thread ID
    state = StateManager.create_initial_state(
        requirements, dialect, enable_critic, generate_nestjs, thread_id
    )
    
    # Initialize checkpointing if enabled
    checkpoint_manager = None
    checkpointer = None
    
    if enable_checkpointing:
        try:
            checkpoint_manager = CheckpointManager(
                checkpointer_type=checkpoint_type,
                connection_string=checkpoint_connection
            )
            
            # Create checkpointer directly (not using context manager for main execution)
            checkpointer = checkpoint_manager.create_checkpointer()
            print(f"✅ Checkpointing enabled: {checkpoint_type.value}")
            print(f"✅ Checkpointer type: {type(checkpointer).__name__}")
            
            # Check if we can resume from existing checkpoint
            try:
                temp_config = CheckpointManager.create_thread_config(thread_id)
                existing_tuple = checkpointer.get_tuple(temp_config)
                if existing_tuple and existing_tuple.checkpoint:
                    existing_state = existing_tuple.checkpoint.get("channel_values")
                    if existing_state:
                        print(f"📂 Found existing checkpoint for thread {thread_id[:8]}...")
                        
                        # Show preview of existing state
                        if "working" in existing_state:
                            working = existing_state["working"]
                            print(f"   Previous state:")
                            print(f"   • Current step: {working.get('current_step', 'N/A')}")
                            print(f"   • Entities: {len(working.get('entities', []))}")
                            print(f"   • Tables: {len(working.get('tables', []))}")
                            print(f"   • Complete: {working.get('is_complete', False)}")
                        
                        # If called interactively (not from continuation), ask to resume
                        if interactive:
                            resume = input("   Resume from this checkpoint? [Y/n]: ").strip().lower()
                            if resume != "n":
                                state = existing_state
                                print("   ✅ Resumed from checkpoint")
                                print("   💡 Continuing with additional requirements...")
                        else:
                            # Auto-resume if not interactive
                            state = existing_state
                            print("   ✅ Auto-resumed from checkpoint")
            except Exception as e:
                # Ignore errors in checkpoint resume check (checkpoint might not exist yet)
                pass
                
        except ImportError as e:
            print(f"⚠️  Checkpointing disabled: {e}")
            checkpointer = None
        except Exception as e:
            print(f"⚠️  Checkpointing error: {e}")
            import traceback
            traceback.print_exc()
            checkpointer = None
    else:
        checkpointer = None
    
    try:
        # Get compiled graphs with checkpointing support
        if checkpointer:
            graph_main, graph_cont = get_compiled_graphs(checkpointer)
        else:
            graph_main, graph_cont = graph, graph_continue
        
        # Create LangSmith config with thread metadata
        config = create_thread_config(
            thread_id=thread_id,
            project_name=project_name,
            run_name="RDBMS Builder - Initial",
            tags=["rdbms-builder", dialect]
        )
        
        # Add checkpoint config for thread-based persistence
        if checkpointer:
            checkpoint_config = CheckpointManager.create_thread_config(thread_id)
            config.update(checkpoint_config)
        
        # Invoke graph with thread tracking and checkpointing
        state = graph_main.invoke(state, config=config)
        
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
                    
                    if checkpointer:
                        checkpoint_config = CheckpointManager.create_thread_config(thread_id)
                        continue_config.update(checkpoint_config)
                    
                    state = graph_cont.invoke(state, config=continue_config)
                else:
                    state["working"]["needs_clarification"] = False
                    continue_config = create_thread_config(
                        thread_id=thread_id,
                        project_name=project_name,
                        run_name="RDBMS Builder - Continue (Auto)",
                        tags=["rdbms-builder", dialect, "continuation"]
                    )
                    
                    if checkpointer:
                        checkpoint_config = CheckpointManager.create_thread_config(thread_id)
                        continue_config.update(checkpoint_config)
                    
                    state = graph_cont.invoke(state, config=continue_config)
        
        print_task_summary(state)
        print_critic_summary(state)
        
        print("\n" + "=" * 60)
        print("🎉 COMPLETE!")
        print(f"📊 LLM Calls: {state['archive']['total_llm_calls']}")
        print(f"🧵 Thread ID: {thread_id}")
        
        if checkpointer and checkpoint_manager:
            checkpoints = checkpoint_manager.list_checkpoints(thread_id, limit=5)
            print(f"💾 Checkpoints Saved: {len(checkpoints)}")
        
        print("=" * 60)
        
        return state
    
    finally:
        # Cleanup checkpointer resources if needed
        if checkpoint_manager:
            checkpoint_manager._cleanup()


def list_previous_threads(
    checkpoint_type: CheckpointerType = CheckpointerType.SQLITE,
    connection_string: Optional[str] = None
) -> list:
    """
    List all previous conversation threads.
    
    Returns:
        List of (thread_id, checkpoint_count, latest_step) tuples
    """
    import sqlite3
    
    if checkpoint_type != CheckpointerType.SQLITE:
        print("⚠️  Thread listing only supported for SQLite currently")
        return []
    
    db_path = connection_string or "./data/checkpoints.db"
    
    if not os.path.exists(db_path):
        return []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                thread_id,
                COUNT(*) as checkpoint_count,
                MAX(json_extract(metadata, '$.step')) as latest_step
            FROM checkpoints
            GROUP BY thread_id
            ORDER BY MAX(rowid) DESC
        """)
        
        threads = cursor.fetchall()
        conn.close()
        
        return threads
    except Exception as e:
        print(f"⚠️  Error listing threads: {e}")
        return []


def select_previous_thread(
    checkpoint_type: CheckpointerType = CheckpointerType.SQLITE,
    connection_string: Optional[str] = None
) -> Optional[str]:
    """
    Allow user to select a previous thread to continue.
    
    Returns:
        Selected thread_id or None
    """
    threads = list_previous_threads(checkpoint_type, connection_string)
    
    if not threads:
        print("\n📝 No previous conversations found.")
        return None
    
    print("\n" + "=" * 60)
    print("📚 PREVIOUS CONVERSATIONS")
    print("=" * 60)
    
    for i, (thread_id, count, step) in enumerate(threads[:10], 1):  # Show last 10
        print(f"\n{i}. Thread: {thread_id[:16]}...")
        print(f"   Checkpoints: {count} | Latest Step: {step or 'N/A'}")
    
    print("\n" + "=" * 60)
    
    choice = input("\nSelect thread number (or press Enter to start new): ").strip()
    
    if not choice:
        return None
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(threads):
            return threads[idx][0]
        else:
            print("❌ Invalid selection")
            return None
    except ValueError:
        print("❌ Invalid input")
        return None


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
    
    # Checkpointing configuration first (to check for previous threads)
    cp = input("Enable checkpointing (long-term memory)? [Y/n]: ").strip().lower()
    enable_checkpointing = cp != "n"
    
    checkpoint_type = CheckpointerType.SQLITE
    checkpoint_connection = None
    resume_thread_id = None
    
    if enable_checkpointing:
        cpt = input("Checkpoint type [1=SQLite (default), 2=PostgreSQL, 3=Memory]: ").strip()
        if cpt == "2":
            checkpoint_type = CheckpointerType.POSTGRES
            checkpoint_connection = input("PostgreSQL URI [default: env var]: ").strip() or None
        elif cpt == "3":
            checkpoint_type = CheckpointerType.MEMORY
        else:
            checkpoint_type = CheckpointerType.SQLITE
            checkpoint_connection = input("SQLite DB path [default: ./data/checkpoints.db]: ").strip() or None
        
        # Ask if user wants to resume a previous conversation
        resume = input("\nContinue a previous conversation? [y/N]: ").strip().lower()
        if resume == "y":
            resume_thread_id = select_previous_thread(checkpoint_type, checkpoint_connection)
            if resume_thread_id:
                print(f"\n✅ Will continue thread: {resume_thread_id[:16]}...")
                # User can provide additional requirements
                additional = input("\nAdditional requirements (or press Enter to continue): ").strip()
                if additional:
                    requirements = additional
    
    d = input("\nDialect [1=PostgreSQL, 2=MySQL, 3=SQLite]: ").strip()
    dialect = {"1": "postgresql", "2": "mysql", "3": "sqlite", "": "postgresql"}.get(d, "postgresql")
    
    c = input("Enable critic? [Y/n]: ").strip().lower()
    enable_critic = c != "n"
    
    n = input("Generate NestJS backend? [Y/n]: ").strip().lower()
    generate_nestjs = n != "n"
    
    result = run_builder(
        requirements,
        dialect,
        enable_critic,
        generate_nestjs,
        enable_checkpointing=enable_checkpointing,
        checkpoint_type=checkpoint_type,
        checkpoint_connection=checkpoint_connection,
        thread_id=resume_thread_id  # Pass the resumed thread_id
    )
    
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