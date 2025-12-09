# utils/llm.py
import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()


def get_llm(temperature: float = 0) -> ChatAnthropic:
    """
    Returns configured LLM instance.
    """
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=temperature,
        max_tokens=8192, # response token limit
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )