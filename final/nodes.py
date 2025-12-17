"""Workflow nodes and routing functions for multi-agent system."""

import json
import re
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from tools.tools import register_multiple_choice_question, get_user_performance, mcq_service
from final.models import AgentState, QuestionOutput, DifficultyReviewOutput
from final.agents import (
    create_question_creator_agent,
    create_difficulty_reviewer_agent,
    create_feedback_agent,
    create_orchestrator_agent
)
from final.logs import (
    log_question_creator,
    log_difficulty_reviewer,
    log_feedback_agent,
    log_orchestrator,
    log_user_output,
    log_separator
)
from final.prompts import (
    QUESTION_CREATOR_PROMPT,
    DIFFICULTY_REVIEWER_PROMPT,
    FEEDBACK_AGENT_PROMPT,
    ORCHESTRATOR_PROMPT
)


def extract_json_from_response(content: str) -> dict:
    """Extracts JSON from LLM response string."""
    if isinstance(content, dict):
        return content

    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        pass

    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from response: {content[:200]}")


import os

def question_creator_node(state: AgentState):
    """Executes Question Creator agent."""
    log_question_creator("Iniciando creación de pregunta...")
    agent = create_question_creator_agent()
    context = ""
    if state.get("difficulty_feedback"):
        context = f"\n\nFeedback del revisor de dificultad: {state['difficulty_feedback']}"

    if state.get("user_feedback"):
        context += f"\n\nFeedback sobre el usuario: {state['user_feedback']}"

    message = f"Crea una nueva pregunta de opción múltiple basada en el material del curso (usa RAG tools).{context}"

    try:
        result = agent.invoke({
            "messages": [
                SystemMessage(content=QUESTION_CREATOR_PROMPT),
                HumanMessage(content=message)
            ]
        })

        response_content = result["messages"][-1].content
        if isinstance(response_content, QuestionOutput):
            validated = response_content
        else:
            json_data = extract_json_from_response(response_content)
            validated = QuestionOutput(**json_data)

        log_question_creator(f"Pregunta creada: {validated.question}")

        return {
            "current_question": validated.question,
            "question_options": validated.options,
            "question_correct_index": validated.correct_index,
            "messages": [AIMessage(content=f"Pregunta propuesta: {validated.question}")],
            "next_action": "review_difficulty"
        }
    except Exception as e:
        log_question_creator(f"Error al crear pregunta: {str(e)}")
        return {
            "messages": [AIMessage(content=f"Error al crear pregunta: {str(e)}")],
            "next_action": "create_question"
        }


def difficulty_reviewer_node(state: AgentState):
    """Executes Difficulty Reviewer agent."""
    log_difficulty_reviewer("Revisando dificultad de la pregunta propuesta...")
    agent = create_difficulty_reviewer_agent()
    score_data = mcq_service.compute_user_score()
    recent_correct = sum(1 for p in score_data['recent_performance'] if p['is_correct'])
    recent_total = len(score_data['recent_performance'])

    if recent_total > 0:
        log_difficulty_reviewer(
            f"Rendimiento del usuario: {recent_correct}/{recent_total} correctas recientes "
            f"({score_data['score_percentage']:.1f}% total)"
        )

    # Build question info for review
    question_info = f"""
PRIMERO: Usa get_performance_tool para obtener el rendimiento detallado del usuario.

Pregunta propuesta: {state['current_question']}

Opciones:
A) {state['question_options'][0]}
B) {state['question_options'][1]}
C) {state['question_options'][2]}
D) {state['question_options'][3]}

Respuesta correcta: {chr(65 + state['question_correct_index'])}

Contexto rápido: El usuario ha respondido {score_data['total_questions']} preguntas totales.
Rendimiento reciente: {recent_correct}/{recent_total} correctas en las últimas respuestas.

INSTRUCCIÓN: Analiza si esta pregunta es apropiadamente desafiante para el nivel actual del usuario.
"""

    message = f"Revisa la siguiente pregunta y determina si la dificultad es apropiada:\n\n{question_info}"

    try:
        result = agent.invoke({
            "messages": [
                SystemMessage(content=DIFFICULTY_REVIEWER_PROMPT),
                HumanMessage(content=message)
            ]
        })

        response_content = result["messages"][-1].content
        if isinstance(response_content, DifficultyReviewOutput):
            validated = response_content
        else:
            json_data = extract_json_from_response(response_content)
            validated = DifficultyReviewOutput(**json_data)

        approved = validated.approved
        feedback = validated.feedback

        log_difficulty_reviewer(f"Decisión: {'✓ APROBADA' if approved else '✗ RECHAZADA'}")
        log_difficulty_reviewer(f"Feedback: {feedback}")

        if approved:
            return {
                "question_approved": True,
                "difficulty_feedback": feedback,
                "messages": [AIMessage(content=f"Pregunta aprobada: {feedback}")],
                "next_action": "present_question"
            }
        else:
            iteration = state.get("iteration_count", 0) + 1
            if iteration >= 3:
                log_difficulty_reviewer("Máximo de iteraciones alcanzado, aprobando pregunta...")
                return {
                    "question_approved": True,
                    "difficulty_feedback": "Aprobada tras múltiples iteraciones",
                    "messages": [AIMessage(content="Pregunta aprobada tras revisión")],
                    "next_action": "present_question"
                }
            else:
                log_difficulty_reviewer(
                    f"⚠️  Pregunta rechazada - Intento {iteration}/3. "
                    f"Solicitando ajuste de dificultad..."
                )
                return {
                    "question_approved": False,
                    "difficulty_feedback": feedback,
                    "iteration_count": iteration,
                    "messages": [AIMessage(content=f"Pregunta rechazada: {feedback}")],
                    "next_action": "create_question"
                }
    except Exception as e:
        log_difficulty_reviewer(f"Error: {str(e)}")
        return {
            "question_approved": True,
            "difficulty_feedback": "Aprobada por defecto tras error",
            "messages": [AIMessage(content=f"Pregunta aprobada (error: {str(e)})")],
            "next_action": "present_question"
        }


def feedback_agent_node(state: AgentState):
    """Executes Feedback Agent."""
    log_feedback_agent("Analizando patrones de aprendizaje del usuario...")

    score_data = mcq_service.compute_user_score()

    if score_data['total_questions'] < 3:
        log_feedback_agent("Historial insuficiente, omitiendo análisis detallado")
        return {
            "user_feedback": "Usuario nuevo, sin suficiente historial para análisis",
            "messages": [AIMessage(content="Historial insuficiente para análisis")],
            "next_action": "create_question"
        }

    agent = create_feedback_agent()

    message = "Analiza el rendimiento del usuario e identifica patrones, fortalezas y áreas de mejora."

    result = agent.invoke({
        "messages": [
            SystemMessage(content=FEEDBACK_AGENT_PROMPT),
            HumanMessage(content=message)
        ]
    })
    response_content = result["messages"][-1].content

    log_feedback_agent(f"Análisis: {response_content[:200]}...")

    return {
        "user_feedback": response_content,
        "messages": [AIMessage(content=response_content)],
        "next_action": "create_question"
    }


def orchestrator_node(state: AgentState):
    """Executes Orchestrator agent."""
    log_orchestrator("Procesando solicitud del usuario...")

    last_message = state["messages"][-1]
    user_request = last_message.content.lower()

    score_data = mcq_service.compute_user_score()
    log_orchestrator(
        f"Score actual: {score_data['score_percentage']:.1f}% "
        f"({score_data['correct_count']}/{score_data['total_questions']})"
    )

    # Route based on user request
    if "pregunta" in user_request or "question" in user_request or "nueva" in user_request:
        log_orchestrator("Solicitud de nueva pregunta detectada")

        if score_data['total_questions'] >= 3:
            log_orchestrator("Historial suficiente, consultando Feedback Agent primero")
            return {"next_action": "get_feedback"}
        else:
            log_orchestrator("Historial insuficiente, procediendo directamente a crear pregunta")
            return {"next_action": "create_question"}

    elif "rendimiento" in user_request or "puntaje" in user_request or "score" in user_request:
        log_orchestrator("Solicitud de rendimiento detectada")
        performance = get_user_performance()
        log_user_output(performance)
        return {"next_action": "end", "messages": [AIMessage(content=performance)]}

    else:
        log_orchestrator("Solicitud general, creando pregunta")
        return {"next_action": "create_question"}


def present_question_node(state: AgentState):
    """Presents approved question to user."""
    log_orchestrator("Pregunta aprobada, registrando y presentando al usuario...")

    question_id = register_multiple_choice_question(
        state["current_question"],
        state["question_options"],
        state["question_correct_index"]
    )

    log_separator()
    log_user_output("\n" + question_id)
    log_separator()

    return {
        "messages": [AIMessage(content=f"Pregunta presentada: {question_id}")],
        "next_action": "end"
    }


def route_orchestrator(state: AgentState) -> Literal["get_feedback", "create_question", "end"]:
    next_action = state.get("next_action", "create_question")
    log_orchestrator(f"Routing: {next_action}")
    return next_action


def route_after_feedback(state: AgentState) -> Literal["create_question"]:
    return "create_question"


def route_after_question_creation(state: AgentState) -> Literal["review_difficulty", "create_question"]:
    if state.get("next_action") == "create_question":
        return "create_question"
    return "review_difficulty"


def route_after_difficulty_review(state: AgentState) -> Literal["create_question", "present_question"]:
    if state.get("question_approved", False):
        return "present_question"
    else:
        log_difficulty_reviewer("Pregunta rechazada, volviendo a Question Creator")
        return "create_question"
