# graph/nodes/clarifier.py
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from graph.state import GraphState, ClarifyingQuestion
from utils.llm import get_llm
from pydantic import BaseModel, Field


class Question(BaseModel):
    question: str = Field(description="The clarifying question to ask")
    context: str = Field(description="Why this question is important")
    options: Optional[List[str]] = Field(default=None, description="Suggested options if applicable")


class ClarificationAnalysis(BaseModel):
    needs_clarification: bool = Field(description="Whether clarification is needed")
    questions: List[Question] = Field(default=[], description="List of clarifying questions")
    analysis_notes: str = Field(description="Brief analysis of the requirements")


SYSTEM_PROMPT = """You are a database architect analyzing software requirements.
Your job is to identify ambiguities, missing information, or unclear aspects that 
would affect database design.

Look for:
1. **Ambiguous cardinality** - Is it one-to-many or many-to-many?
2. **Missing entities** - Are there implied entities not explicitly mentioned?
3. **Unclear attributes** - What data should be stored for each entity?
4. **Business rules** - Are there constraints or rules that affect the schema?
5. **Scale considerations** - Expected data volume, performance requirements?
6. **Temporal aspects** - Do we need to track history or just current state?
7. **Authentication/Authorization** - Are there users, roles, permissions?
8. **Soft delete vs hard delete** - How should deletion be handled?
9. **Multi-tenancy** - Single tenant or multi-tenant?
10. **Audit requirements** - Need to track who changed what and when?

IMPORTANT:
- Only ask questions that SIGNIFICANTLY impact database design
- Maximum 5 questions
- If requirements are clear enough, set needs_clarification to false
- Provide helpful options when applicable
"""


def clarifier(state: GraphState) -> Dict[str, Any]:
    """
    Node that analyzes requirements and generates clarifying questions.
    """
    print("\n🤔 Analyzing requirements for clarity...")
    
    llm = get_llm()
    structured_llm = llm.with_structured_output(ClarificationAnalysis)
    
    # Build context including any previous answers
    context = f"Requirements:\n{state['user_requirements']}"
    
    if state.get('user_answers'):
        context += "\n\nPrevious clarifications provided by user:\n"
        for i, answer in enumerate(state['user_answers'], 1):
            context += f"{i}. {answer}\n"
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""{context}

Analyze these requirements and determine if clarification is needed.
If the requirements are clear enough for database design, set needs_clarification to false.""")
    ]
    
    try:
        result: ClarificationAnalysis = structured_llm.invoke(messages)
        
        if result.needs_clarification and result.questions:
            print(f"❓ Found {len(result.questions)} questions to clarify:")
            for q in result.questions:
                print(f"   • {q.question}")
            
            questions = [
                {
                    "question": q.question,
                    "context": q.context,
                    "options": q.options
                }
                for q in result.questions
            ]
            
            return {
                "clarifying_questions": questions,
                "needs_clarification": True,
                "current_step": "clarification_needed"
            }
        else:
            print("✅ Requirements are clear enough to proceed")
            return {
                "clarifying_questions": [],
                "needs_clarification": False,
                "current_step": "clarification_complete"
            }
            
    except Exception as e:
        print(f"⚠️ Error in clarification: {e}, proceeding anyway")
        return {
            "clarifying_questions": [],
            "needs_clarification": False,
            "current_step": "clarification_complete"
        }