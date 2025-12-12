# graph/nodes/nestjs_generator.py
from typing import List, Optional, Dict
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import GraphState
from utils.llm import get_llm
from utils.state_manager import StateManager
from utils.context_builder import ContextBuilder
from utils.task_manager import start_task, complete_task, fail_task
from pydantic import BaseModel, Field


# ============================================================
# PYDANTIC MODELS FOR STRUCTURED OUTPUT
# ============================================================

class SimpleEndpoint(BaseModel):
    """Simplified endpoint schema - just the essentials"""
    method: str = Field(description="HTTP method")
    path: str = Field(description="Route path like /api/users/:id")
    description: str = Field(description="Brief description")


class SimpleModule(BaseModel):
    """Simplified module schema"""
    name: str = Field(description="Module name in PascalCase")
    entities: List[str] = Field(description="Entities this module manages")
    key_endpoints: List[str] = Field(description="List of key endpoint paths like ['/api/users', '/api/users/:id']")


class EventPattern(BaseModel):
    """Event-driven architecture pattern"""
    event_name: str = Field(description="Event name like 'user.created', 'vehicle.location.updated'")
    trigger: str = Field(description="What triggers this event")
    consumers: List[str] = Field(description="Services/modules that consume this event")
    purpose: str = Field(description="Why this event is needed (max 10 words)")


class NestJSArchitectureSchema(BaseModel):
    """Simplified architecture schema - focus on core structure"""
    project_name: str = Field(description="Project name")
    description: str = Field(description="Brief system description")
    modules: List[SimpleModule] = Field(description="Application modules (one per main entity)")
    key_endpoints: List[SimpleEndpoint] = Field(description="Most important API endpoints (max 10)")
    security_guards: List[str] = Field(default=[], description="Guard names like ['JwtAuthGuard', 'RolesGuard']")
    environment_variables: List[str] = Field(default=[], description="Required env vars like ['DATABASE_URL', 'JWT_SECRET']")
    event_patterns: List[EventPattern] = Field(default=[], description="Event-driven patterns if needed for real-time/async operations")
    message_queue: Optional[str] = Field(default=None, description="Message queue technology if events are used (e.g., 'RabbitMQ', 'Redis', 'AWS SQS')")


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """You are a NestJS architect. Generate a concise backend architecture blueprint.

Focus on:
1. **Modules**: One module per main entity (PascalCase: UserModule, ProductModule)
2. **Key Endpoints**: List the 8-10 most important API endpoints with HTTP methods
3. **Security**: Essential guards (JwtAuthGuard, RolesGuard, etc.)
4. **Environment**: Required environment variables
5. **Event-Driven Architecture**: 
   - Analyze if events are needed for: real-time updates, async processing, notifications, webhooks
   - If yes: define key events (e.g., user.created, location.updated) and which modules emit/consume them
   - Suggest message queue (RabbitMQ, Redis, AWS SQS) if events are used

Keep it simple and practical. The team will expand details during implementation."""


# ============================================================
# DIAGRAM GENERATORS
# ============================================================

def generate_module_diagram(modules: List[SimpleModule]) -> str:
    """Generate a simple Mermaid diagram showing module structure."""
    lines = ["graph TD"]
    lines.append("    AppModule[AppModule]")
    
    for module in modules:
        module_id = module.name.replace(" ", "")
        entities = ", ".join(module.entities)
        lines.append(f"    {module_id}[{module.name}Module<br/>{entities}]")
        lines.append(f"    AppModule --> {module_id}")
    
    return "\n".join(lines)


def generate_request_flow_diagram() -> str:
    """Generate a generic Mermaid sequence diagram showing typical request flow."""
    return """sequenceDiagram
    participant Client
    participant Controller
    participant Guard
    participant Service
    participant Repository
    participant Database
    
    Client->>+Controller: HTTP Request
    Controller->>+Guard: Validate Auth
    Guard-->>-Controller: Authorized
    Controller->>+Service: Business Logic
    Service->>+Repository: Query Data
    Repository->>+Database: SQL Query
    Database-->>-Repository: Result Set
    Repository-->>-Service: Entity Data
    Service-->>-Controller: Response DTO
    Controller-->>-Client: HTTP Response"""


def generate_endpoint_table(endpoints: List[SimpleEndpoint]) -> str:
    """Generate a markdown table of key endpoints."""
    lines = ["| Method | Endpoint | Description |"]
    lines.append("|--------|----------|-------------|")
    
    for ep in endpoints:
        lines.append(f"| {ep.method} | `{ep.path}` | {ep.description} |")
    
    return "\n".join(lines)


def generate_directory_structure(modules: List[SimpleModule]) -> str:
    """Generate the recommended directory structure."""
    lines = [
        "src/",
        "├── app.module.ts",
        "├── main.ts",
        "├── common/",
        "│   ├── guards/",
        "│   ├── interceptors/",
        "│   ├── pipes/",
        "│   └── decorators/",
        "├── config/",
    ]
    
    for i, module in enumerate(modules):
        module_path = to_kebab_case(module.name)
        is_last = i == len(modules) - 1
        prefix = "└──" if is_last else "├──"
        
        lines.extend([
            f"{prefix} {module_path}/",
            f"│   ├── {module_path}.module.ts",
            f"│   ├── {module_path}.controller.ts",
            f"│   ├── {module_path}.service.ts",
            f"│   ├── entities/",
            f"│   └── dto/",
        ])
    
    return "\n".join(lines)


def to_kebab_case(name: str) -> str:
    """Convert PascalCase to kebab-case."""
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("-")
        result.append(char.lower())
    return "".join(result)


# ============================================================
# CONVERSION TO STATE TYPES
# ============================================================

def convert_to_architecture(schema: NestJSArchitectureSchema) -> dict:
    """Convert simplified Pydantic schema to architecture dictionary."""
    
    # Generate diagrams
    module_diagram = generate_module_diagram(schema.modules)
    flow_diagram = generate_request_flow_diagram()
    endpoint_table = generate_endpoint_table(schema.key_endpoints)
    directory_structure = generate_directory_structure(schema.modules)
    
    # Convert modules
    modules = [
        {
            "name": m.name,
            "description": f"Manages {', '.join(m.entities)}",
            "entities": m.entities,
            "has_controller": True,
            "has_service": True,
            "has_repository": True,
            "dependencies": [],
        }
        for m in schema.modules
    ]
    
    # Convert entities
    entities = []
    for module in schema.modules:
        for entity in module.entities:
            entities.append({
                "name": entity,
                "table_name": to_kebab_case(entity) + "s",
                "columns": [],
                "relations": [],
            })
    
    # Convert endpoints
    endpoints = [
        {
            "method": ep.method,
            "path": ep.path,
            "description": ep.description,
            "request_dto": None,
            "response_dto": None,
        }
        for ep in schema.key_endpoints
    ]
    
    # Convert event patterns
    event_patterns = [
        {
            "event_name": ep.event_name,
            "trigger": ep.trigger,
            "consumers": ep.consumers,
            "purpose": ep.purpose
        }
        for ep in schema.event_patterns
    ]
    
    return {
        "project_name": schema.project_name,
        "description": schema.description,
        "modules": modules,
        "entities": entities,
        "endpoints": endpoints,
        "shared_dtos": [],
        "guards": schema.security_guards,
        "interceptors": ["LoggingInterceptor", "TransformInterceptor"],
        "directory_structure": directory_structure,
        "module_diagram": module_diagram,
        "flow_diagrams": {"Generic Request Flow": flow_diagram},
        "endpoint_table": endpoint_table,
        "guards_detail": [{"name": g, "purpose": "Authentication/Authorization", "applies_to": ["All protected routes"]} for g in schema.security_guards],
        "interceptors_detail": [
            {"name": "LoggingInterceptor", "purpose": "Request/Response logging", "applies_to": ["Global"]},
            {"name": "TransformInterceptor", "purpose": "Response transformation", "applies_to": ["Global"]}
        ],
        "pipes": [{"name": "ValidationPipe", "purpose": "DTO validation"}],
        "middlewares": [{"name": "LoggerMiddleware", "purpose": "HTTP request logging", "routes": ["*"]}],
        "data_flows": [],
        "environment_variables": schema.environment_variables,
        "external_integrations": [],
        "code_samples": {},
        "event_patterns": event_patterns,
        "message_queue": schema.message_queue,
    }


# ============================================================
# MAIN NODE FUNCTION
# ============================================================

def nestjs_generator(state: GraphState) -> GraphState:
    """Generate NestJS backend architecture blueprint based on the database schema."""
    start_task(state, "generate_nestjs")
    
    working = state["working"]
    tables = working["tables"]
    requirements = working["user_requirements"]
    
    if not tables:
        fail_task(state, "generate_nestjs", "No tables found in schema")
        return state
    
    llm = get_llm()  # Reduced tokens for simplified output
    structured_llm = llm.with_structured_output(NestJSArchitectureSchema)
    
    # Build context from schema
    context = ContextBuilder.for_nestjs_architecture(state)
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""Generate a concise NestJS architecture blueprint.

## Business Requirements
{requirements}

## Database Schema
{context}

Generate:
1. Modules (one per main entity/domain)
2. API endpoints with a short description
3. Essential security guards
4. Required environment variables
5. Is event driven architecture needed ? If yes, how to implement it for the given schema?

Keep it brief and actionable.""")
    ]
    
    try:
        result = structured_llm.invoke(messages)
        StateManager.increment_llm_calls(state)
        
        architecture = convert_to_architecture(result)
        
        state["archive"]["nestjs_architecture"] = architecture
        state["working"]["current_step"] = "nestjs_generation_complete"
        
        complete_task(
            state, 
            "generate_nestjs", 
            f"Generated architecture: {len(architecture['modules'])} modules, {len(architecture['endpoints'])} endpoints"
        )
        
    except Exception as e:
        fail_task(state, "generate_nestjs", str(e))
        state["working"]["current_step"] = "error"
    
    return state
