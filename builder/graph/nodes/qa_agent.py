# graph/nodes/qa_agent.py
"""
Q&A Agent Node

Answers questions about previously generated database schemas and NestJS architecture.
Uses long-term memory (checkpointed state) to provide context-aware answers.
"""

from ..state import GraphState
from ...utils.llm import get_llm
from ...utils.state_manager import StateManager
from ...utils.task_manager import create_task, start_task, complete_task


def qa_agent(state: GraphState) -> dict:
    """
    Answer questions about previously generated outputs using long-term memory.
    
    This node provides intelligent, context-aware responses based on:
    - Previously generated database schema
    - NestJS architecture
    - Entities and relationships
    - Design decisions and rationale
    """
    working = state["working"]
    archive = state["archive"]
    
    task_id = create_task(state, "qa_agent", "Answering question about previous output")
    start_task(state, task_id)
    
    user_question = working["user_requirements"]
    
    # Build comprehensive context from checkpointed state
    context_parts = []
    
    # Add entities context
    if working.get("entities"):
        entities_summary = "\n".join([
            f"- {e['name']}: {e.get('description', 'N/A')}"
            for e in working["entities"][:10]
        ])
        context_parts.append(f"## Entities\n{entities_summary}")
    
    # Add tables context
    if working.get("tables"):
        tables_summary = "\n".join([
            f"- {t['name']}: {t.get('description', 'N/A')} ({len(t.get('columns', []))} columns)"
            for t in working["tables"][:15]
        ])
        context_parts.append(f"## Database Tables\n{tables_summary}")
    
    # Add DDL script context (truncated)
    if archive.get("ddl_script"):
        ddl = archive["ddl_script"]
        if len(ddl) > 2000:
            ddl = ddl[:2000] + "\n... (truncated)"
        context_parts.append(f"## SQL Schema\n```sql\n{ddl}\n```")
    
    # Add NestJS architecture context
    if archive.get("nestjs_architecture"):
        arch = archive["nestjs_architecture"]
        modules = arch.get("modules", [])
        endpoints = arch.get("endpoints", [])
        
        modules_summary = "\n".join([
            f"- {m['name']}Module: {', '.join(m.get('entities', []))}"
            for m in modules[:10]
        ])
        
        endpoints_summary = "\n".join([
            f"- {e['method']} {e['path']}: {e.get('description', '')[:60]}"
            for e in endpoints[:15]
        ])
        
        context_parts.append(f"## NestJS Modules\n{modules_summary}")
        context_parts.append(f"## API Endpoints\n{endpoints_summary}")
    
    # Add task history for design decisions
    if archive.get("tasks"):
        recent_tasks = [t for t in archive["tasks"][-5:] if t.get("result")]
        if recent_tasks:
            task_summary = "\n".join([
                f"- {t['content']}: {t.get('result', '')[:100]}"
                for t in recent_tasks
            ])
            context_parts.append(f"## Recent Design Decisions\n{task_summary}")
    
    context = "\n\n".join(context_parts)
    
    prompt = f"""You are an expert software architect and database designer. 

The user previously asked you to design a system, and you generated a database schema and NestJS backend architecture.

Now the user has a question about the generated output. Use the following context to provide a detailed, accurate, and helpful answer.

## Context from Previous Generation

{context}

## User's Question

"{user_question}"

## Instructions

1. Answer the question directly and clearly
2. Reference specific parts of the generated output when relevant
3. Provide examples or code snippets if helpful
4. If suggesting improvements, explain the rationale
5. If the question is unclear, ask for clarification

Provide a comprehensive answer:"""
    
    try:
        llm = get_llm()
        StateManager.increment_llm_calls(state)
        
        response = llm.invoke(prompt)
        answer = response.content if hasattr(response, 'content') else str(response)
        
        # Store the Q&A in archive for future reference
        qa_entry = {
            "question": user_question,
            "answer": answer,
            "timestamp": StateManager.get_timestamp()
        }
        
        qa_history = archive.get("qa_history", [])
        qa_history.append(qa_entry)
        
        result = {
            "working": {
                "current_step": "qa_complete",
                "last_answer": answer
            },
            "archive": {
                "qa_history": qa_history
            }
        }
        
        complete_task(state, task_id, "Question answered successfully")
        
        return result
        
    except Exception as e:
        from utils.task_manager import fail_task
        fail_task(state, task_id, str(e))
        return {
            "working": {
                "error": f"Q&A failed: {str(e)}",
                "last_answer": "I apologize, but I encountered an error while processing your question. Please try rephrasing it."
            }
        }


def get_timestamp():
    """Get current timestamp."""
    from datetime import datetime
    return datetime.now().isoformat()


# Add this helper to StateManager
StateManager.get_timestamp = staticmethod(get_timestamp)

