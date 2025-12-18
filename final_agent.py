import os
import sys
from langgraph.graph import StateGraph, END, START
from dotenv import load_dotenv
from colorama import Fore, Style, init as colorama_init
from langchain_core.messages import HumanMessage

# Configurar encoding UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from tools.tools import (
    check_last_multiple_choice_answer,
    get_unified_performance
)
from services.service_manager import (
    initialize_session_services,
    get_service
)
from final.models import AgentState
from final.nodes import (
    orchestrator_node,
    feedback_agent_node,
    question_creator_node,
    open_question_creator_node,
    open_answer_evaluator_node,
    difficulty_reviewer_node,
    present_question_node,
    route_orchestrator,
    route_after_feedback,
    route_after_question_creation,
    route_after_difficulty_review
)
from final.logs import log_separator, log_user_input, log_user_output

load_dotenv()
colorama_init(autoreset=True)


def build_workflow():
    workflow = StateGraph(AgentState)

    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("get_feedback", feedback_agent_node)
    workflow.add_node("create_mcq_question", question_creator_node)
    workflow.add_node("create_open_question", open_question_creator_node)
    workflow.add_node("review_difficulty", difficulty_reviewer_node)
    workflow.add_node("present_question", present_question_node)

    workflow.add_edge(START, "orchestrator")
    workflow.add_conditional_edges(
        "orchestrator",
        route_orchestrator,
        {
            "get_feedback": "get_feedback",
            "create_mcq_question": "create_mcq_question",
            "create_open_question": "create_open_question",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "get_feedback",
        route_after_feedback,
        {
            "create_mcq_question": "create_mcq_question",
            "create_open_question": "create_open_question"
        }
    )

    workflow.add_conditional_edges(
        "create_mcq_question",
        route_after_question_creation,
        {
            "review_difficulty": "review_difficulty",
            "create_mcq_question": "create_mcq_question"
        }
    )

    workflow.add_conditional_edges(
        "create_open_question",
        route_after_question_creation,
        {
            "review_difficulty": "review_difficulty",
            "create_open_question": "create_open_question"
        }
    )

    workflow.add_conditional_edges(
        "review_difficulty",
        route_after_difficulty_review,
        {
            "create_mcq_question": "create_mcq_question",
            "create_open_question": "create_open_question",
            "present_question": "present_question"
        }
    )

    workflow.add_edge("present_question", END)

    return workflow.compile()


def build_evaluation_workflow():
    """Separate workflow for evaluating open-ended answers"""
    workflow = StateGraph(AgentState)

    workflow.add_node("evaluate_answer", open_answer_evaluator_node)

    workflow.add_edge(START, "evaluate_answer")
    workflow.add_edge("evaluate_answer", END)

    return workflow.compile()


def main():
    """Main execution loop."""
    initialize_session_services()

    log_separator()
    print(f"{Fore.CYAN}{Style.BRIGHT}🚀 SISTEMA MULTI-AGENTE DE GENERACIÓN DE PREGUNTAS{Style.RESET_ALL}")

    # Show configuration status
    use_rag = os.environ.get("USE_RAG", "true").lower() == "true"
    use_open_ended = os.environ.get("USE_OPEN_ENDED_QUESTIONS", "false").lower() == "true"

    rag_status = f"{Fore.GREEN}HABILITADO" if use_rag else f"{Fore.YELLOW}DESHABILITADO"
    open_status = f"{Fore.GREEN}HABILITADO" if use_open_ended else f"{Fore.YELLOW}DESHABILITADO"

    print(f"{Fore.CYAN}RAG: {rag_status}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Preguntas Abiertas: {open_status}{Style.RESET_ALL}")

    log_separator()

    app = build_workflow()
    evaluation_app = build_evaluation_workflow()

    waiting_for_answer = False
    waiting_for_open_answer = False
    last_question_id = None
    last_question_type = None

    print("\nComandos disponibles:")
    print("  - 'pregunta' / 'nueva pregunta': Genera una nueva pregunta")
    print("  - 'rendimiento' / 'puntaje': Muestra tu rendimiento actual")
    print("  - 'A', 'B', 'C', 'D': Responde pregunta MCQ")
    print("  - [texto largo]: Responde pregunta abierta")
    print("  - 'salir' / 'exit': Termina el programa")
    print()

    while True:
        log_separator()

        # Dynamic prompt based on state
        if waiting_for_open_answer:
            prompt_text = f"{Fore.YELLOW}💭 Tu respuesta (texto desarrollado): {Style.RESET_ALL}"
        elif waiting_for_answer:
            prompt_text = f"{Fore.YELLOW}💭 Tu respuesta (A/B/C/D): {Style.RESET_ALL}"
        else:
            prompt_text = f"{Fore.BLUE}👤 Tu mensaje: {Style.RESET_ALL}"

        user_input = input(prompt_text).strip()

        if not user_input:
            continue

        # Check for exit commands
        if user_input.lower() in ['salir', 'exit', 'quit']:
            log_user_output("¡Hasta luego!")
            break

        log_user_input(user_input)
        log_separator()

        # Handle MCQ answer
        if waiting_for_answer and not waiting_for_open_answer:
            if user_input.lower().startswith(('a)', 'b)', 'c)', 'd)')) or \
               (len(user_input) == 1 and user_input.upper() in 'ABCD'):
                result_msg = check_last_multiple_choice_answer(user_input)
                log_separator()
                log_user_output("\n" + result_msg + "\n")
                log_separator()

            score_data = get_service().compute_user_score()
            if score_data['total_questions'] > 0:
                # Show unified performance
                perf_msg = get_unified_performance()
                print(f"\n{perf_msg}\n")

                waiting_for_answer = False
                last_question_id = None
                last_question_type = None

                print(
                    f"{Fore.GREEN}✅ Respuesta registrada. "
                    f"Puedes pedir otra pregunta.{Style.RESET_ALL}\n"
                )
                continue

        # Handle Open-Ended answer
        if waiting_for_open_answer:
            # Detect if it's an open-ended answer (longer text)
            if len(user_input) > 10:  # Heuristic: open answers are longer
                from final.logs import log_orchestrator
                log_orchestrator("Detectada respuesta abierta, iniciando evaluación...")

                # Invoke evaluation workflow
                eval_state = {
                    "messages": [],
                    "question_id": last_question_id,
                    "user_open_answer": user_input,
                    "next_action": "",
                    "question_type": "",
                    "current_question": "",
                    "question_options": [],
                    "question_correct_index": 0,
                    "open_question": "",
                    "open_evaluation_criteria": "",
                    "open_key_concepts": [],
                    "open_question_difficulty": "",
                    "difficulty_feedback": "",
                    "user_feedback": "",
                    "score_data": {},
                    "iteration_count": 0,
                    "question_approved": False,
                    "question_type_decision": "",
                    "evaluation_score": 0.0,
                    "evaluation_feedback": "",
                    "evaluation_passing": False
                }

                try:
                    result = evaluation_app.invoke(eval_state)

                    # Display evaluation feedback
                    if result.get("messages") and len(result["messages"]) > 0:
                        evaluation_msg = result["messages"][-1].content
                        log_separator()
                        log_user_output(evaluation_msg)
                        log_separator()
                    else:
                        log_user_output("⚠️  No se recibió feedback de evaluación")

                    # Show unified performance
                    perf_msg = get_unified_performance()
                    print(f"\n{perf_msg}\n")

                    waiting_for_open_answer = False
                    waiting_for_answer = False
                    last_question_id = None
                    last_question_type = None

                    print(
                        f"{Fore.GREEN}✅ Evaluación completada. "
                        f"Puedes pedir otra pregunta.{Style.RESET_ALL}\n"
                    )
                except Exception as e:
                    import traceback
                    log_user_output(f"Error en evaluación: {str(e)}")
                    print(f"{Fore.RED}Traceback completo:{Style.RESET_ALL}")
                    traceback.print_exc()

                continue

        # Process commands through the multi-agent system
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "question_type": "",
            "current_question": "",
            "question_options": [],
            "question_correct_index": 0,
            "open_question": "",
            "open_evaluation_criteria": "",
            "open_key_concepts": [],
            "open_question_difficulty": "",
            "difficulty_feedback": "",
            "user_feedback": "",
            "score_data": {},
            "iteration_count": 0,
            "question_approved": False,
            "next_action": "",
            "question_type_decision": "",
            "question_id": "",
            "user_open_answer": "",
            "evaluation_score": 0.0,
            "evaluation_feedback": "",
            "evaluation_passing": False
        }

        try:
            result = app.invoke(initial_state)

            # Check what type of question was presented
            if result.get("question_id"):
                last_question_id = result["question_id"]
                last_question_type = result.get("question_type", "mcq")

                if last_question_type == "open_ended":
                    waiting_for_open_answer = True
                    waiting_for_answer = False
                    print(f"\n{Fore.YELLOW}⏳ Esperando tu respuesta desarrollada...{Style.RESET_ALL}\n")
                else:
                    waiting_for_answer = True
                    waiting_for_open_answer = False
                    print(f"\n{Fore.YELLOW}⏳ Esperando tu respuesta (A/B/C/D)...{Style.RESET_ALL}\n")

        except Exception as e:
            log_user_output(f"Error en el sistema: {str(e)}")
            continue


if __name__ == "__main__":
    main()
