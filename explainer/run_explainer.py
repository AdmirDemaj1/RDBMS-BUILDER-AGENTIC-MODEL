"""
Explainer Subgraph

Handles user questions about the generated backend.
Retrieves information from memory and explains it to the user.
"""
from typing import Optional, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from builder.utils.llm import get_llm


def run_explainer(
    user_question: str,
    backend_context: Optional[Dict[str, Any]] = None,
    interactive: bool = True
) -> str:
    """
    Run the explainer to answer user questions about the generated backend.
    
    Args:
        user_question: The user's question about the backend
        backend_context: Context from the generated backend (schema, entities, etc.)
        interactive: Whether to print output
    
    Returns:
        The explanation as a string
    """
    if interactive:
        print("\n" + "=" * 60)
        print("🔍 BACKEND EXPLAINER")
        print("=" * 60)
    
    # Build context from backend results
    context_parts = []
    
    if backend_context:
        # Extract DDL script
        if backend_context.get("ddl_script"):
            ddl = backend_context["ddl_script"]
            # Truncate if too long
            if len(ddl) > 3000:
                ddl = ddl[:3000] + "\n... (truncated)"
            context_parts.append(f"## Database Schema (DDL)\n```sql\n{ddl}\n```")
        
        # Extract entities
        working = backend_context.get("working", {})
        entities = working.get("entities", [])
        if entities:
            entity_names = [e.get("name", "Unknown") for e in entities[:10]]
            context_parts.append(f"## Entities\n{', '.join(entity_names)}")
        
        # Extract tables
        tables = working.get("tables", [])
        if tables:
            table_info = []
            for t in tables[:10]:
                cols = [c.get("name", "?") for c in t.get("columns", [])[:5]]
                table_info.append(f"- {t.get('name', 'Unknown')}: {', '.join(cols)}")
            context_parts.append(f"## Tables\n" + "\n".join(table_info))
        
        # Extract ERD
        if backend_context.get("erd_diagram"):
            context_parts.append(f"## ERD Diagram\n```mermaid\n{backend_context['erd_diagram'][:1000]}\n```")
        
        # Extract NestJS info
        nestjs = backend_context.get("nestjs_architecture")
        if nestjs:
            modules = nestjs.get("modules", [])
            module_names = [m.get("name", "?") for m in modules[:10]]
            endpoints = nestjs.get("endpoints", [])
            context_parts.append(f"## NestJS Architecture\n- Modules: {', '.join(module_names)}\n- Endpoints: {len(endpoints)}")
    
    context = "\n\n".join(context_parts) if context_parts else "No backend has been generated yet."
    
    system_prompt = """You are an expert backend developer and database architect.
Your role is to explain the generated backend system to users in a clear, helpful way.

When explaining:
- Be concise but thorough
- Use simple language for non-technical users
- Highlight key design decisions and their benefits
- Explain relationships between entities
- If asked about specific parts, focus on those

If no backend has been generated, let the user know they need to build one first."""

    user_prompt = f"""Based on the following generated backend:

{context}

User Question: {user_question}

Please provide a clear explanation."""

    try:
        llm = get_llm()
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        explanation = response.content
        
        if interactive:
            print(f"\n📖 Explanation:\n")
            print(explanation)
            print("\n" + "=" * 60)
        
        return explanation
        
    except Exception as e:
        error_msg = f"Error generating explanation: {str(e)}"
        if interactive:
            print(f"\n❌ {error_msg}")
        return error_msg

