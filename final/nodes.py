"""Workflow nodes and routing functions for multi-agent system."""

import json
import re
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from tools.tools import (
    register_multiple_choice_question,
    register_open_ended_question,
    evaluate_open_ended_answer,
    get_user_performance,
    get_unified_performance
)
from services.service_manager import get_service, get_open_service, get_unified_performance as get_unified_perf_service
from final.models import (
    AgentState,
    QuestionOutput,
    OpenEndedQuestionOutput,
    OpenEndedEvaluationOutput,
    DifficultyReviewOutput
)
from final.agents import (
    create_question_creator_agent,
    create_open_question_creator_agent,
    create_open_answer_evaluator_agent,
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
    OPEN_ENDED_QUESTION_CREATOR_PROMPT,
    OPEN_ENDED_ANSWER_EVALUATOR_PROMPT,
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

    # Use appropriate prompt and message based on RAG availability
    use_rag = os.environ.get("USE_RAG", "true").lower() == "true"

    if use_rag:
        prompt = QUESTION_CREATOR_PROMPT
        message = f"Crea una nueva pregunta de opción múltiple basada en el material del curso (usa RAG tools).{context}"
    else:
        from final.prompts import QUESTION_CREATOR_PROMPT_NO_RAG
        prompt = QUESTION_CREATOR_PROMPT_NO_RAG
        # Include content path if available
        content_path = os.environ.get("CONTENT_PATH", "")
        if content_path:
            message = f"Crea una nueva pregunta de opción múltiple basada en el material del curso. El archivo del curso está en: {content_path}{context}"
        else:
            message = f"Crea una nueva pregunta de opción múltiple basada en el material del curso.{context}"

    try:
        result = agent.invoke({
            "messages": [
                SystemMessage(content=prompt),
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


def open_question_creator_node(state: AgentState):
    """Executes Open-Ended Question Creator agent."""
    log_question_creator("Iniciando creación de pregunta abierta...")
    agent = create_open_question_creator_agent()
    context = ""
    if state.get("difficulty_feedback"):
        context = f"\n\nFeedback del revisor de dificultad: {state['difficulty_feedback']}"

    if state.get("user_feedback"):
        context += f"\n\nFeedback sobre el usuario: {state['user_feedback']}"

    # Use appropriate prompt and message based on RAG availability
    use_rag = os.environ.get("USE_RAG", "true").lower() == "true"

    if use_rag:
        prompt = OPEN_ENDED_QUESTION_CREATOR_PROMPT
        message = f"Crea una nueva pregunta abierta basada en el material del curso (usa RAG tools).{context}"
    else:
        from final.prompts import OPEN_ENDED_QUESTION_CREATOR_PROMPT_NO_RAG
        prompt = OPEN_ENDED_QUESTION_CREATOR_PROMPT_NO_RAG
        content_path = os.environ.get("CONTENT_PATH", "")
        if content_path:
            message = f"Crea una nueva pregunta abierta basada en el material del curso. El archivo del curso está en: {content_path}{context}"
        else:
            message = f"Crea una nueva pregunta abierta basada en el material del curso.{context}"

    try:
        result = agent.invoke({
            "messages": [
                SystemMessage(content=prompt),
                HumanMessage(content=message)
            ]
        })

        response_content = result["messages"][-1].content
        if isinstance(response_content, OpenEndedQuestionOutput):
            validated = response_content
        else:
            json_data = extract_json_from_response(response_content)
            validated = OpenEndedQuestionOutput(**json_data)

        log_question_creator(f"Pregunta abierta creada: {validated.question}")

        return {
            "question_type": "open_ended",
            "open_question": validated.question,
            "open_evaluation_criteria": validated.evaluation_criteria,
            "open_key_concepts": validated.key_concepts,
            "open_question_difficulty": validated.difficulty_level,
            "messages": [AIMessage(content=f"Pregunta abierta propuesta: {validated.question}")],
            "next_action": "review_difficulty"
        }
    except Exception as e:
        log_question_creator(f"Error al crear pregunta abierta: {str(e)}")
        return {
            "messages": [AIMessage(content=f"Error al crear pregunta abierta: {str(e)}")],
            "next_action": "create_open_question"
        }


def open_answer_evaluator_node(state: AgentState):
    """Evaluates user's open-ended answer."""
    log_orchestrator("Evaluando respuesta abierta del usuario...")

    agent = create_open_answer_evaluator_agent()

    question_id = state.get("question_id")
    if not question_id:
        return {
            "messages": [AIMessage(content="Error: No se proporcionó question_id")],
            "next_action": "end"
        }

    open_service = get_open_service()
    question_data = open_service.get_question(question_id)
    if not question_data:
        return {
            "messages": [AIMessage(content="Error: No se encontró la pregunta")],
            "next_action": "end"
        }

    evaluation_context = f"""
Pregunta: {question_data['question']}

Criterios de evaluación:
{question_data['evaluation_criteria']}

Conceptos clave esperados:
{', '.join(question_data['key_concepts'])}

Respuesta del usuario:
{state['user_open_answer']}

INSTRUCCIÓN: Evalúa la respuesta del usuario asignando un puntaje de 0.0 a 10.0.
Considera:
- Presencia de conceptos clave
- Precisión técnica
- Profundidad de comprensión
- Claridad de expresión

Un puntaje de 7.0 o superior se considera aprobado.
"""

    try:
        result = agent.invoke({
            "messages": [
                SystemMessage(content=OPEN_ENDED_ANSWER_EVALUATOR_PROMPT),
                HumanMessage(content=evaluation_context)
            ]
        })

        response_content = result["messages"][-1].content
        if isinstance(response_content, OpenEndedEvaluationOutput):
            validated = response_content
        else:
            json_data = extract_json_from_response(response_content)
            validated = OpenEndedEvaluationOutput(**json_data)

        # Store evaluation
        evaluation_msg = evaluate_open_ended_answer(
            question_id,
            state['user_open_answer'],
            validated.score,
            validated.feedback,
            validated.is_passing,
            validated.strengths,
            validated.weaknesses
        )

        log_orchestrator(f"Evaluación completada: {validated.score:.1f}/10")
        log_separator()
        log_user_output(evaluation_msg)
        log_separator()

        return {
            "evaluation_score": validated.score,
            "evaluation_feedback": validated.feedback,
            "evaluation_passing": validated.is_passing,
            "messages": [AIMessage(content=evaluation_msg)],
            "next_action": "end"
        }
    except Exception as e:
        log_orchestrator(f"Error en evaluación: {str(e)}")
        # Provide default evaluation in case of error
        default_msg = evaluate_open_ended_answer(
            question_id,
            state['user_open_answer'],
            5.0,
            f"Error al evaluar respuesta: {str(e)}. Se asigna puntaje neutral.",
            False,
            [],
            ["Error en evaluación automática"]
        )
        return {
            "evaluation_score": 5.0,
            "evaluation_feedback": str(e),
            "evaluation_passing": False,
            "messages": [AIMessage(content=default_msg)],
            "next_action": "end"
        }


def difficulty_reviewer_node(state: AgentState):
    """Executes Difficulty Reviewer agent - handles both MCQ and Open-Ended."""
    log_difficulty_reviewer("Revisando dificultad de la pregunta propuesta...")
    agent = create_difficulty_reviewer_agent()

    # Get unified performance
    unified_perf = get_unified_perf_service()
    unified_data = unified_perf.compute_unified_performance()

    log_difficulty_reviewer(
        f"Rendimiento global: {unified_data['overall_percentage']:.1f}% "
        f"(MCQ: {unified_data['mcq_percentage']:.1f}%, Open: {unified_data['open_percentage']:.1f}%)"
    )

    question_type = state.get("question_type", "mcq")

    if question_type == "open_ended":
        question_info = f"""
PRIMERO: Usa get_unified_performance_tool para obtener rendimiento completo.

Pregunta Abierta propuesta: {state['open_question']}

Criterios de evaluación:
{state['open_evaluation_criteria']}

Conceptos clave: {', '.join(state['open_key_concepts'])}
Dificultad esperada: {state['open_question_difficulty']}

Contexto rápido: El usuario ha respondido {unified_data['total_questions']} preguntas totales.
Performance global: {unified_data['overall_percentage']:.1f}%

INSTRUCCIÓN: Analiza si esta pregunta abierta es apropiadamente desafiante para el nivel actual del usuario.
"""
    else:  # MCQ
        mcq_service = get_service()
        score_data = get_service().compute_user_score()
        recent_correct = sum(1 for p in score_data['recent_performance'] if p['is_correct'])
        recent_total = len(score_data['recent_performance'])

        question_info = f"""
PRIMERO: Usa get_unified_performance_tool para obtener rendimiento completo.

Pregunta MCQ propuesta: {state['current_question']}

Opciones:
A) {state['question_options'][0]}
B) {state['question_options'][1]}
C) {state['question_options'][2]}
D) {state['question_options'][3]}

Respuesta correcta: {chr(65 + state['question_correct_index'])}

Contexto rápido: El usuario ha respondido {unified_data['total_questions']} preguntas totales.
Rendimiento reciente MCQ: {recent_correct}/{recent_total} correctas en las últimas respuestas.
Performance global: {unified_data['overall_percentage']:.1f}%

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
        f"Performance global: {unified_data['overall_percentage']:.1f}% "
        f"(Open-ended: {'HABILITADO' if use_open_ended else 'DESHABILITADO'})"
    )

    # Route based on user request
    if "pregunta" in user_request or "question" in user_request or "nueva" in user_request:
        log_orchestrator("Solicitud de nueva pregunta detectada")

        # Decide question type based on performance
        overall_percentage = unified_data['overall_percentage']
        threshold = float(os.environ.get("OPEN_ENDED_THRESHOLD", "70.0"))

        if use_open_ended and overall_percentage >= threshold:
            log_orchestrator(
                f"✓ Performance >= {threshold}% ({overall_percentage:.1f}%) - "
                "Usuario calificado para preguntas abiertas"
            )
            question_decision = "open"
        else:
            if use_open_ended and overall_percentage < threshold:
                log_orchestrator(
                    f"✗ Performance < {threshold}% ({overall_percentage:.1f}%) - "
                    "Manteniendo preguntas MCQ"
                )
            question_decision = "mcq"

        # Decide if feedback analysis is needed
        if unified_data['total_questions'] >= 3:
            log_orchestrator("Historial suficiente, consultando Feedback Agent")
            return {
                "next_action": "get_feedback",
                "question_type_decision": question_decision
            }
        else:
            log_orchestrator(f"Creando pregunta tipo: {question_decision}")
            return {
                "next_action": f"create_{question_decision}_question",
                "question_type_decision": question_decision
            }

    elif "rendimiento" in user_request or "puntaje" in user_request or "score" in user_request:
        log_orchestrator("Solicitud de rendimiento detectada")
        performance = get_unified_performance()
        log_user_output(performance)
        return {"next_action": "end", "messages": [AIMessage(content=performance)]}

    else:
        log_orchestrator("Solicitud general de pregunta")

        # Decide question type based on performance (same logic as keyword match)
        overall_percentage = unified_data['overall_percentage']
        threshold = float(os.environ.get("OPEN_ENDED_THRESHOLD", "70.0"))

        if use_open_ended and overall_percentage >= threshold:
            log_orchestrator(
                f"✓ Performance >= {threshold}% ({overall_percentage:.1f}%) - "
                "Usuario calificado para preguntas abiertas"
            )
            question_decision = "open"
        else:
            if use_open_ended and overall_percentage < threshold:
                log_orchestrator(
                    f"✗ Performance < {threshold}% ({overall_percentage:.1f}%) - "
                    "Manteniendo preguntas MCQ"
                )
            question_decision = "mcq"

        # Decide if feedback analysis is needed
        if unified_data['total_questions'] >= 3:
            log_orchestrator("Historial suficiente, consultando Feedback Agent")
            return {
                "next_action": "get_feedback",
                "question_type_decision": question_decision
            }
        else:
            log_orchestrator(f"Creando pregunta tipo: {question_decision}")
            return {
                "next_action": f"create_{question_decision}_question",
                "question_type_decision": question_decision
            }


def present_question_node(state: AgentState):
    """Presents approved question to user - handles both MCQ and Open-Ended."""
    question_type = state.get("question_type", "mcq")

    if question_type == "open_ended":
        log_orchestrator("Pregunta abierta aprobada, registrando...")
        question_id = register_open_ended_question(
            state["open_question"],
            state["open_evaluation_criteria"],
            state["open_key_concepts"],
            state["open_question_difficulty"]
        )
    else:
        log_orchestrator("Pregunta MCQ aprobada, registrando...")
        question_id = register_multiple_choice_question(
            state["current_question"],
            state["question_options"],
            state["question_correct_index"]
        )

    log_separator()
    log_user_output("\n" + question_id)
    log_separator()

    return {
        "question_id": question_id,  # Store ID for later evaluation
        "messages": [AIMessage(content=f"Pregunta presentada: {question_id}")],
        "next_action": "end"
    }


def route_orchestrator(state: AgentState) -> Literal["get_feedback", "create_mcq_question", "create_open_question", "end"]:
    next_action = state.get("next_action", "create_mcq_question")
    log_orchestrator(f"Routing: {next_action}")
    return next_action


def route_after_feedback(state: AgentState) -> Literal["create_mcq_question", "create_open_question"]:
    question_type = state.get("question_type_decision", "mcq")
    if question_type == "open":
        return "create_open_question"
    return "create_mcq_question"


def route_after_question_creation(state: AgentState) -> Literal["review_difficulty", "create_mcq_question", "create_open_question"]:
    next_action = state.get("next_action")
    question_type = state.get("question_type", "mcq")

    if next_action == "review_difficulty":
        return "review_difficulty"
    elif question_type == "open_ended":
        return "create_open_question"
    else:
        return "create_mcq_question"


def route_after_difficulty_review(state: AgentState) -> Literal["create_mcq_question", "create_open_question", "present_question"]:
    if state.get("question_approved", False):
        return "present_question"

    question_type = state.get("question_type", "mcq")
    if question_type == "open_ended":
        log_difficulty_reviewer("Pregunta rechazada, volviendo a Open Question Creator")
        return "create_open_question"
    else:
        log_difficulty_reviewer("Pregunta rechazada, volviendo a MCQ Question Creator")
        return "create_mcq_question"
