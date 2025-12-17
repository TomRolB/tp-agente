import os
import sys
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from final.agent_tools import (
    read_text_file_tool,
    search_in_text_file_tool,
    list_questions_tool,
    get_performance_tool,
    get_history_tool
)


def create_model():
    """
    Create LLM model with provider priority:
    1. OpenAI (if OPENAI_API_KEY is set)
    2. Groq (if GROQ_API_KEY is set)
    3. Crash if neither is available
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    
    if openai_key:
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=2048,
            timeout=None,
            max_retries=2
        )
    
    if groq_key:
        return ChatGroq(
            model="moonshotai/kimi-k2-instruct-0905",
            temperature=0.7,
            max_tokens=2048,
            timeout=None,
            max_retries=2
        )
    
    print("ERROR: No API key found. Please set either OPENAI_API_KEY or GROQ_API_KEY in your .env file.")
    sys.exit(1)


def create_question_creator_agent():
    tools = [read_text_file_tool, search_in_text_file_tool, list_questions_tool]
    llm = create_model()
    return create_agent(llm, tools)


def create_difficulty_reviewer_agent():
    tools = [get_performance_tool]
    llm = create_model()
    return create_agent(llm, tools)


def create_feedback_agent():
    tools = [get_performance_tool, get_history_tool]
    llm = create_model()
    return create_agent(llm, tools)


def create_orchestrator_agent():
    tools = [get_performance_tool]
    llm = create_model()
    return create_agent(llm, tools)
