from langchain_core.tools import tool
from tools.tools import (
    read_text_file,
    search_in_text_file,
    list_multiple_choice_questions,
    get_user_performance,
    get_answer_history_detailed,
    get_unified_performance,
    load_content_from_directory
)
from services.service_manager import get_service

# Initialize RAG components
_vector_store = None
_retriever = None

def get_rag_components():
    global _vector_store, _retriever

    if _vector_store is None:
        from final.rag.vector_store import ChromaVectorStore
        from final.rag.retriever import ContentRetriever

        _vector_store = ChromaVectorStore()
        _retriever = ContentRetriever(_vector_store)

    return _vector_store, _retriever


@tool
def read_text_file_tool(file_path: str) -> str:
    """Read complete file content"""
    return read_text_file(file_path)


@tool
def search_in_text_file_tool(file_path: str, search_term: str, case_sensitive: bool = False) -> str:
    """Search for term in file"""
    return search_in_text_file(file_path, search_term, case_sensitive)


@tool
def list_questions_tool(limit: int = 20) -> str:
    """List recent questions"""
    return list_multiple_choice_questions(limit)


@tool
def get_performance_tool() -> str:
    """Get user performance stats"""
    return get_user_performance()


@tool
def get_history_tool() -> str:
    """Get answer history"""
    return get_answer_history_detailed()


@tool
def get_unified_performance_tool() -> str:
    """Get unified performance across MCQ and Open-Ended questions"""
    return get_unified_performance()


@tool
def load_course_content_tool() -> str:
    """
    Load all course content from the content directory.
    Use this when RAG is disabled to access course materials.
    Returns: Combined content from all .txt files in CONTENT_DIR
    """
    return load_content_from_directory()


# ===== RAG TOOLS =====

@tool
def retrieve_content_tool(query: str, n_results: int = 3) -> str:
    """
    Retrieve relevant content from course material using RAG
    Returns: Formatted content with the most relevant fragments
    """
    try:
        _, retriever = get_rag_components()
        return retriever.retrieve_relevant_content(query, n_results)
    except Exception as e:
        return f"Error al recuperar contenido: {str(e)}"


@tool
def get_topic_content_tool(topic: str, n_results: int = 3) -> str:
    """
    Get content about a specific topic using RAG to create a question about it.
    Returns: Formatted content suitable for creating a question
    """
    try:
        _, retriever = get_rag_components()
        return retriever.retrieve_for_question_creation(topic=topic, n_results=n_results)
    except Exception as e:
        return f"Error al obtener contenido del tema: {str(e)}"


@tool
def analyze_weak_areas_tool() -> str:
    """
    Analyze user's weak areas by retrieving course content related to questions they answered incorrectly.
    Returns: Content related to the user's incorrect answers
    """
    try:
        # Obtener preguntas incorrectas del usuario
        mcq_service = get_service()
        score_data = mcq_service.compute_user_score()
        incorrect_questions = [
            p['question'] for p in score_data['recent_performance']
            if not p['is_correct']
        ]

        if not incorrect_questions:
            return "El usuario no tiene respuestas incorrectas recientes. Está respondiendo todo correctamente."

        _, retriever = get_rag_components()
        return retriever.retrieve_related_to_errors(incorrect_questions)
    except Exception as e:
        return f"Error al analizar áreas débiles: {str(e)}"


@tool
def search_concept_tool(concept: str, n_results: int = 2) -> str:
    """
    Search for a specific concept in the course material using RAG.
    Returns: Content explaining the concept
    """
    try:
        _, retriever = get_rag_components()
        return retriever.search_specific_concept(concept, n_results)
    except Exception as e:
        return f"Error al buscar concepto: {str(e)}"
