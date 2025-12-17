from langgraph.graph import StateGraph, END, START
from dotenv import load_dotenv
from colorama import Fore, Style, init as colorama_init
from langchain_core.messages import HumanMessage

from tools.tools import check_last_multiple_choice_answer
from services.service_manager import get_service
from final.models import AgentState
from final.nodes import (
    orchestrator_node,
    feedback_agent_node,
    question_creator_node,
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
    workflow.add_node("create_question", question_creator_node)
    workflow.add_node("review_difficulty", difficulty_reviewer_node)
    workflow.add_node("present_question", present_question_node)

    workflow.add_edge(START, "orchestrator")
    workflow.add_conditional_edges(
        "orchestrator",
        route_orchestrator,
        {
            "get_feedback": "get_feedback",
            "create_question": "create_question",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "get_feedback",
        route_after_feedback,
        {"create_question": "create_question"}
    )

    workflow.add_conditional_edges(
        "create_question",
        route_after_question_creation,
        {"review_difficulty": "review_difficulty"}
    )

    workflow.add_conditional_edges(
        "review_difficulty",
        route_after_difficulty_review,
        {
            "create_question": "create_question",
            "present_question": "present_question"
        }
    )

    workflow.add_edge("present_question", END)

    return workflow.compile()


def main():
    """Main execution loop."""
    log_separator()
    print(f"{Fore.CYAN}{Style.BRIGHT}🚀 SISTEMA MULTI-AGENTE DE GENERACIÓN DE PREGUNTAS{Style.RESET_ALL}")
    log_separator()

    app = build_workflow()
    waiting_for_answer = False

    print("\nComandos disponibles:")
    print("  - 'pregunta' / 'nueva pregunta': Genera una nueva pregunta")
    print("  - 'rendimiento' / 'puntaje': Muestra tu rendimiento actual")
    print("  - 'A', 'B', 'C', 'D': Responde la pregunta actual")
    print("  - 'salir' / 'exit': Termina el programa")
    print()

    while True:
        log_separator()

        # Change prompt based on whether we're waiting for an answer
        if waiting_for_answer:
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

        if user_input.lower().startswith(('a)', 'b)', 'c)', 'd)')) or \
           (len(user_input) == 1 and user_input.upper() in 'ABCD'):
            result_msg = check_last_multiple_choice_answer(user_input)
            log_separator()
            log_user_output("\n" + result_msg + "\n")
            log_separator()

            score_data = get_service().compute_user_score()
            if score_data['total_questions'] > 0:
                print(
                    f"\n{Fore.CYAN}📊 Score actual: {score_data['score_percentage']:.1f}% " +
                    f"({score_data['correct_count']}/{score_data['total_questions']} correctas)"
                    f"{Style.RESET_ALL}\n"
                )

            waiting_for_answer = False
            print(
                f"{Fore.GREEN}✅ Respuesta registrada. "
                f"Puedes pedir otra pregunta o ver tu rendimiento.{Style.RESET_ALL}\n"
            )
            continue

        # Process other commands through the multi-agent system
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "current_question": "",
            "question_options": [],
            "question_correct_index": 0,
            "difficulty_feedback": "",
            "user_feedback": "",
            "score_data": {},
            "iteration_count": 0,
            "question_approved": False,
            "next_action": ""
        }

        try:
            result = app.invoke(initial_state)
            # Check if a question was just presented
            if result.get("current_question"):
                waiting_for_answer = True
                print(f"\n{Fore.YELLOW}⏳ Esperando tu respuesta...{Style.RESET_ALL}\n")
        except Exception as e:
            log_user_output(f"Error en el sistema: {str(e)}")
            continue


if __name__ == "__main__":
    main()
