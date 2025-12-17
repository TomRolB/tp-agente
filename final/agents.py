import os
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from final.agent_tools import (
    read_text_file_tool,
    search_in_text_file_tool,
    list_questions_tool,
    get_performance_tool,
    get_history_tool,
    retrieve_content_tool,
    get_topic_content_tool,
    analyze_weak_areas_tool,
    search_concept_tool
)

# Check if RAG is enabled
USE_RAG = os.environ.get("USE_RAG", "true").lower() == "true"


def create_model():
    return ChatOpenAI(
        model="gpt-4o",  # or "gpt-4", "gpt-3.5-turbo", etc.
        temperature=0.7,
        max_tokens=2048,
        timeout=None,
        max_retries=2
    )


def create_question_creator_agent():
    tools = [
        read_text_file_tool,
        search_in_text_file_tool,
        list_questions_tool
    ]

    # Add RAG tools only if enabled
    if USE_RAG:
        tools.extend([
            retrieve_content_tool,
            get_topic_content_tool,
            search_concept_tool
        ])

    llm = create_model()
    return create_agent(llm, tools)


def create_difficulty_reviewer_agent():
    tools = [get_performance_tool]
    llm = create_model()
    return create_agent(llm, tools)


def create_feedback_agent():
    tools = [
        get_performance_tool,
        get_history_tool
    ]

    # Add RAG tools only if enabled
    if USE_RAG:
        tools.append(analyze_weak_areas_tool)

    llm = create_model()
    return create_agent(llm, tools)


def create_orchestrator_agent():
    tools = [get_performance_tool]
    llm = create_model()
    return create_agent(llm, tools)
