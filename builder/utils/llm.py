# utils/llm.py
import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()


def get_llm(temperature: float = 0, max_tokens: int = 4096) -> ChatAnthropic:
    """
    Returns configured LLM instance.
    """
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=temperature,
        max_tokens=max_tokens,  # response token limit
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )