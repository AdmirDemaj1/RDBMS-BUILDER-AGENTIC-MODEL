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

class EndpointSchema(BaseModel):
    method: str = Field(description="HTTP method: GET, POST, PUT, PATCH, DELETE")
    path: str = Field(description="Full route path like /api/users/:id")
    description: str = Field(description="What this endpoint does")
    request_body: Optional[str] = Field(default=None, description="Request body description or DTO name")
    response: str = Field(description="Response description")
    auth_required: bool = Field(default=True, description="Whether authentication is required")
    roles: List[str] = Field(default=[], description="Required roles if any")


class ModuleSchema(BaseModel):
    name: str = Field(description="Module name in PascalCase")
    description: str = Field(description="What this module handles")
    entities: List[str] = Field(description="Database entities this module manages")
    dependencies: List[str] = Field(default=[], description="Other modules this depends on")
    endpoints: List[EndpointSchema] = Field(default=[], description="REST endpoints for this module")


class DataFlowStep(BaseModel):
    step: int = Field(description="Step number in the flow")
    component: str = Field(description="Component name: Controller, Service, Repository, etc.")
    action: str = Field(description="What happens at this step")


class DataFlow(BaseModel):
    name: str = Field(description="Flow name like 'Create User' or 'Get Vehicle List'")
    trigger: str = Field(description="What triggers this flow, e.g., 'POST /api/users'")
    steps: List[DataFlowStep] = Field(description="Steps in the data flow")


class GuardSchema(BaseModel):
    name: str = Field(description="Guard name like JwtAuthGuard, RolesGuard")
    purpose: str = Field(description="What this guard protects/validates")
    applies_to: List[str] = Field(description="Endpoints or modules it applies to")


class InterceptorSchema(BaseModel):
    name: str = Field(description="Interceptor name")
    purpose: str = Field(description="What this interceptor does")
    applies_to: List[str] = Field(description="Where it's applied: global, module, or specific endpoints")


class PipeSchema(BaseModel):
    name: str = Field(description="Pipe name like ValidationPipe")
    purpose: str = Field(description="What this pipe does")


class MiddlewareSchema(BaseModel):
    name: str = Field(description="Middleware name")
    purpose: str = Field(description="What this middleware handles")
    routes: List[str] = Field(description="Routes this middleware applies to")


class NestJSArchitectureSchema(BaseModel):
    project_name: str = Field(description="Project name")
    description: str = Field(description="Brief description of the backend system")
    modules: List[ModuleSchema] = Field(description="Application modules")
    data_flows: List[DataFlow] = Field(description="Key data flow examples showing request lifecycle")
    guards: List[GuardSchema] = Field(default=[], description="Authentication/Authorization guards")
    interceptors: List[InterceptorSchema] = Field(default=[], description="Request/Response interceptors")
    pipes: List[PipeSchema] = Field(default=[], description="Data transformation/validation pipes")
    middlewares: List[MiddlewareSchema] = Field(default=[], description="HTTP middlewares")
    environment_variables: List[str] = Field(default=[], description="Required environment variables")
    external_integrations: List[str] = Field(default=[], description="External services/APIs to integrate")


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """You are an expert NestJS architect. Generate a comprehensive backend architecture blueprint based on the database schema and business requirements provided.

DO NOT generate actual code. Instead, provide a detailed architecture documentation that includes:

## ARCHITECTURE COMPONENTS

1. **Modules**: Group related functionality into cohesive modules
   - Each module should manage specific entities
   - Define clear module boundaries and dependencies
   - Follow domain-driven design principles

2. **Endpoints**: Define all REST API endpoints
   - Use RESTful conventions (GET, POST, PUT, PATCH, DELETE)
   - Include path parameters and query parameters
   - Specify authentication and authorization requirements
   - Document request/response structures

3. **Data Flows**: Show how requests flow through the system
   - Controller → Service → Repository → Database
   - Include validation, transformation, and error handling steps
   - Show where guards and interceptors are applied

4. **Security**: Define authentication and authorization
   - Guards for protecting routes
   - Role-based access control
   - JWT or other auth mechanisms

5. **Cross-cutting Concerns**:
   - Interceptors for logging, caching, response transformation
   - Pipes for validation and data transformation
   - Middlewares for request preprocessing

## NAMING CONVENTIONS

- **Modules**: PascalCase (e.g., UserModule, VehicleModule)
- **Endpoints**: kebab-case paths (e.g., /api/users, /api/fuel-logs)
- **Guards**: PascalCase + Guard (e.g., JwtAuthGuard, RolesGuard)

## BEST PRACTICES

- Group CRUD operations per entity
- Add business-specific endpoints beyond basic CRUD
- Consider pagination for list endpoints
- Include filtering and sorting capabilities
- Define proper HTTP status codes
- Plan for error handling

Generate a complete architecture blueprint that a development team can use to implement the NestJS backend."""


# ============================================================
# DIAGRAM GENERATORS
# ============================================================

def generate_module_diagram(modules: List[ModuleSchema]) -> str:
    """Generate a Mermaid diagram showing module dependencies."""
    lines = ["graph TD"]
    lines.append("    subgraph Application")
    lines.append("        AppModule[AppModule]")
    
    for module in modules:
        module_id = module.name.replace(" ", "")
        lines.append(f"        {module_id}[{module.name}Module]")
        lines.append(f"        AppModule --> {module_id}")
    
    lines.append("    end")
    lines.append("")
    
    # Add dependencies
    for module in modules:
        module_id = module.name.replace(" ", "")
        for dep in module.dependencies:
            dep_id = dep.replace(" ", "").replace("Module", "")
            lines.append(f"    {module_id} -.-> {dep_id}")
    
    return "\n".join(lines)


def generate_request_flow_diagram(flow: DataFlow) -> str:
    """Generate a Mermaid sequence diagram for a data flow."""
    lines = ["sequenceDiagram"]
    lines.append("    participant Client")
    
    # Extract unique components
    components = []
    for step in flow.steps:
        if step.component not in components:
            components.append(step.component)
    
    for comp in components:
        lines.append(f"    participant {comp}")
    
    lines.append(f"    Note over Client: {flow.trigger}")
    
    prev_comp = "Client"
    for step in flow.steps:
        lines.append(f"    {prev_comp}->>+{step.component}: {step.action}")
        prev_comp = step.component
    
    # Return flow
    for comp in reversed(components):
        if comp != components[-1]:
            lines.append(f"    {comp}-->>-{prev_comp}: Response")
            prev_comp = comp
    
    lines.append(f"    {components[0]}-->>-Client: HTTP Response")
    
    return "\n".join(lines)


def generate_endpoint_table(modules: List[ModuleSchema]) -> str:
    """Generate a markdown table of all endpoints."""
    lines = ["| Method | Endpoint | Description | Auth | Roles |"]
    lines.append("|--------|----------|-------------|------|-------|")
    
    for module in modules:
        for ep in module.endpoints:
            roles = ", ".join(ep.roles) if ep.roles else "-"
            auth = "✓" if ep.auth_required else "✗"
            lines.append(f"| {ep.method} | `{ep.path}` | {ep.description} | {auth} | {roles} |")
    
    return "\n".join(lines)


def generate_directory_structure(modules: List[ModuleSchema]) -> str:
    """Generate the recommended directory structure."""
    lines = [
        "src/",
        "├── app.module.ts",
        "├── main.ts",
        "├── common/",
        "│   ├── guards/",
        "│   │   ├── jwt-auth.guard.ts",
        "│   │   └── roles.guard.ts",
        "│   ├── interceptors/",
        "│   │   ├── logging.interceptor.ts",
        "│   │   └── transform.interceptor.ts",
        "│   ├── pipes/",
        "│   │   └── validation.pipe.ts",
        "│   ├── decorators/",
        "│   │   └── roles.decorator.ts",
        "│   └── filters/",
        "│       └── http-exception.filter.ts",
        "├── config/",
        "│   └── configuration.ts",
    ]
    
    for module in modules:
        module_path = to_kebab_case(module.name)
        entity_name = module.entities[0] if module.entities else module.name
        entity_path = to_kebab_case(entity_name)
        
        lines.extend([
            f"├── {module_path}/",
            f"│   ├── {module_path}.module.ts",
            f"│   ├── {module_path}.controller.ts",
            f"│   ├── {module_path}.service.ts",
            f"│   ├── entities/",
            f"│   │   └── {entity_path}.entity.ts",
            f"│   └── dto/",
            f"│       ├── create-{entity_path}.dto.ts",
            f"│       └── update-{entity_path}.dto.ts",
        ])
    
    lines.append("└── database/")
    lines.append("    └── database.module.ts")
    
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
    """Convert Pydantic schema to architecture dictionary."""
    
    # Generate diagrams
    module_diagram = generate_module_diagram(schema.modules)
    
    flow_diagrams = {}
    for flow in schema.data_flows:
        flow_diagrams[flow.name] = generate_request_flow_diagram(flow)
    
    endpoint_table = generate_endpoint_table(schema.modules)
    directory_structure = generate_directory_structure(schema.modules)
    
    # Convert modules
    modules = [
        {
            "name": m.name,
            "description": m.description,
            "entities": m.entities,
            "has_controller": True,
            "has_service": True,
            "has_repository": True,
            "dependencies": m.dependencies,
        }
        for m in schema.modules
    ]
    
    # Convert entities (simplified - just names from modules)
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
    endpoints = []
    for module in schema.modules:
        for ep in module.endpoints:
            endpoints.append({
                "method": ep.method,
                "path": ep.path,
                "description": ep.description,
                "request_dto": ep.request_body,
                "response_dto": ep.response,
            })
    
    return {
        "project_name": schema.project_name,
        "description": schema.description,
        "modules": modules,
        "entities": entities,
        "endpoints": endpoints,
        "shared_dtos": [],
        "guards": [g.name for g in schema.guards],
        "interceptors": [i.name for i in schema.interceptors],
        "directory_structure": directory_structure,
        "module_diagram": module_diagram,
        "flow_diagrams": flow_diagrams,
        "endpoint_table": endpoint_table,
        "guards_detail": [{"name": g.name, "purpose": g.purpose, "applies_to": g.applies_to} for g in schema.guards],
        "interceptors_detail": [{"name": i.name, "purpose": i.purpose, "applies_to": i.applies_to} for i in schema.interceptors],
        "pipes": [{"name": p.name, "purpose": p.purpose} for p in schema.pipes],
        "middlewares": [{"name": m.name, "purpose": m.purpose, "routes": m.routes} for m in schema.middlewares],
        "data_flows": [{"name": f.name, "trigger": f.trigger, "steps": [{"step": s.step, "component": s.component, "action": s.action} for s in f.steps]} for f in schema.data_flows],
        "environment_variables": schema.environment_variables,
        "external_integrations": schema.external_integrations,
        "code_samples": {},  # Empty - no code generation
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
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(NestJSArchitectureSchema)
    
    # Build context from schema
    context = ContextBuilder.for_nestjs_architecture(state)
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""Generate a NestJS backend architecture blueprint for the following database schema and business requirements.

## Business Requirements
{requirements}

## Database Schema
{context}

Generate a comprehensive architecture documentation including:
1. Module structure with clear boundaries
2. All REST API endpoints with authentication requirements
3. Key data flow examples showing request lifecycle
4. Security guards and interceptors
5. Required environment variables and external integrations

Focus on architecture design, NOT code implementation.""")
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
