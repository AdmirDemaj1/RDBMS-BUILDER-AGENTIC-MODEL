# graph/nodes/clarifier.py
from typing import List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import GraphState
from utils.llm import get_llm
from utils.state_manager import StateManager
from utils.task_manager import start_task, complete_task, fail_task
from pydantic import BaseModel, Field


class Question(BaseModel):
    question: str
    context: str
    options: Optional[List[str]] = None


class ClarificationAnalysis(BaseModel):
    needs_clarification: bool
    questions: List[Question] = []
    analysis_notes: str


SYSTEM_PROMPT = """Analyze requirements for database design ambiguities.

Check for unclear:
- Entity boundaries (is Product one entity or Product/ProductVariant?)
- Cardinality (1:1, 1:N, M:N) and optional vs required relationships
- Key attributes and enum/status values
- Uniqueness constraints and business rules

Rules:
- Max 5 questions, only if SIGNIFICANTLY impacts schema
- Provide context on WHY clarification matters
- Suggest options when applicable
- Set needs_clarification=false if requirements are clear
- Skip UI/implementation concerns"""


def clarifier(state: GraphState) -> GraphState:
    start_task(state, "clarify")
    
    working = state["working"]
    requirements = working["user_requirements"]
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(ClarificationAnalysis)
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Requirements:\n{requirements[:1500]}")
    ]
    
    try:
        result = structured_llm.invoke(messages)
        StateManager.increment_llm_calls(state)
        
        if result.needs_clarification and result.questions:
            questions = [
                {"question": q.question, "context": q.context, "options": q.options}
                for q in result.questions
            ]
            
            state["archive"]["clarifying_questions"] = questions
            state["working"]["needs_clarification"] = True
            state["working"]["current_step"] = "clarification_needed"
            
            complete_task(state, "clarify", f"Found {len(questions)} questions")
        else:
            state["working"]["needs_clarification"] = False
            state["working"]["current_step"] = "clarification_complete"
            complete_task(state, "clarify", "Requirements clear")
            
    except Exception as e:
        fail_task(state, "clarify", str(e))
        state["working"]["needs_clarification"] = False
        state["working"]["current_step"] = "clarification_complete"
    
    return state