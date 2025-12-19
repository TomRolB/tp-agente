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
    get_history_tool,
    retrieve_content_tool,
    get_topic_content_tool,
    analyze_weak_areas_tool,
    search_concept_tool,
    load_course_content_tool
)

# Check if RAG is enabled
USE_RAG = os.environ.get("USE_RAG", "true").lower() == "true"


def validate_api_keys():
    """
    Validate that at least one API key is configured.
    Exits the program if none is found.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    if not openai_key and not anthropic_key and not groq_key:
        print("=" * 80, file=sys.stderr)
        print("ERROR: No API key found!", file=sys.stderr)
        print("Please set one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, or GROQ_API_KEY", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        sys.exit(1)


def create_model():
    """
    Create LLM model with provider priority:
    1. OpenAI (if OPENAI_API_KEY is set)
    2. Anthropic (if ANTHROPIC_API_KEY is set)
    3. Groq (if GROQ_API_KEY is set)
    """
    validate_api_keys()

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            max_tokens=2048,
            timeout=None,
            max_retries=2
        )

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model="claude-sonnet-4-5-20250929",
                temperature=0.7,
                max_tokens=2048,
                timeout=None,
                max_retries=2
            )
        except ImportError:
            print("Warning: ANTHROPIC_API_KEY is set but langchain-anthropic is not installed.", file=sys.stderr)
            print("Install with: pip install langchain-anthropic", file=sys.stderr)
            print("Falling back to Groq...", file=sys.stderr)

    return ChatGroq(
        model="moonshotai/kimi-k2-instruct-0905",
        temperature=0.7,
        max_tokens=2048,
        timeout=None,
        max_retries=2
    )


def create_question_creator_agent():
    tools = [
        list_questions_tool
    ]

    # Add RAG tools if enabled, otherwise add content loader
    if USE_RAG:
        tools.extend([
            retrieve_content_tool,
            get_topic_content_tool,
            search_concept_tool
        ])
    else:
        tools.extend([
            load_course_content_tool,
            read_text_file_tool,
            search_in_text_file_tool
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


def create_open_question_creator_agent():
    """Creates Open-Ended Question Creator agent"""
    tools = [
        list_questions_tool
    ]

    # Add RAG tools if enabled, otherwise add content loader
    if USE_RAG:
        tools.extend([
            retrieve_content_tool,
            get_topic_content_tool,
            search_concept_tool
        ])
    else:
        tools.extend([
            load_course_content_tool,
            read_text_file_tool,
            search_in_text_file_tool
        ])

    llm = create_model()
    return create_agent(llm, tools)


def create_open_answer_evaluator_agent():
    """Creates Open-Ended Answer Evaluator agent"""
    tools = []  # No necesita tools, solo evalúa
    llm = create_model()
    return create_agent(llm, tools)
