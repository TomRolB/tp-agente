import chainlit as cl
from services.service_manager import initialize_session_services, get_service
from final_agent import build_workflow
from langchain_core.messages import HumanMessage
from tools.tools import check_last_multiple_choice_answer

class ChainlitHandler:
    @staticmethod
    async def init_session():
        """Initialize user session with isolated services."""
        # Initialize all services (MCQ, Open-Ended, Unified)
        initialize_session_services()

        # Store service in user session for reference
        service = get_service()
        cl.user_session.set("mcq_service", service)

        app = build_workflow()
        cl.user_session.set("app", app)
        
        await cl.Message(
            content="¡Hola! Soy tu asistente de aprendizaje. Puedo generar preguntas de opción múltiple para ayudarte a estudiar. \n\nEscribe 'nueva pregunta' para comenzar o pídeme revisar tu rendimiento."
        ).send()

    @staticmethod
    async def process_message(message: cl.Message):
        """Handle incoming user messages."""
        service, app = ChainlitHandler._restore_context()
        user_input = message.content.strip()

        if message.elements:
            await ChainlitHandler._handle_file_upload(message)
            return

        if ChainlitHandler._is_answer_attempt(user_input):
            await ChainlitHandler._handle_answer(user_input, service)
            return

        await ChainlitHandler._run_agent(app, user_input)

    @staticmethod
    async def process_action(action: cl.Action):
        """Handle button clicks."""
        # Extract the value from the action payload
        action_value = action.payload.get("value", action.payload)
        await cl.Message(content=action_value, author="User").send()
        await ChainlitHandler.process_message(cl.Message(content=action_value))

    # --- Private Helpers ---

    @staticmethod
    def _restore_context():
        """Restore ContextVars from session."""
        service = cl.user_session.get("mcq_service")
        set_service(service)
        app = cl.user_session.get("app")
        return service, app

    @staticmethod
    async def _handle_file_upload(message: cl.Message):
        """Handle file upload scenarios."""
        await cl.Message(content="Recibí un archivo, pero aún no sé cómo procesarlo.").send()

    @staticmethod
    def _is_answer_attempt(text: str) -> bool:
        """Check if input looks like a multiple choice answer (A, B, C, D)."""
        text = text.lower()
        return text.startswith(('a)', 'b)', 'c)', 'd)')) or \
               (len(text) == 1 and text.upper() in 'ABCD')

    @staticmethod
    async def _handle_answer(user_input: str, service: MCQService):
        """Process a multiple choice answer."""
        result_msg = check_last_multiple_choice_answer(user_input)
        await cl.Message(content=result_msg).send()
        
        score_data = service.compute_user_score()
        if score_data['total_questions'] > 0:
            score_msg = (
                f"📊 Score actual: {score_data['score_percentage']:.1f}% "
                f"({score_data['correct_count']}/{score_data['total_questions']} correctas)"
            )
            await cl.Message(content=score_msg).send()
        
        actions = [
            cl.Action(name="new_question", payload={"value": "nueva pregunta"}, label="Nueva Pregunta"),
            cl.Action(name="performance", payload={"value": "rendimiento"}, label="Ver Rendimiento")
        ]
        await cl.Message(content="¿Qué te gustaría hacer ahora?", actions=actions).send()

    @staticmethod
    async def _run_agent(app, user_input: str):
        """Execute the agent workflow."""
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

        msg = cl.Message(content="")
        await msg.send() # Placeholder for potential streaming

        # Use ainvoke to get final state in one go
        result = await app.ainvoke(initial_state)
        await ChainlitHandler._render_agent_result(result)

    @staticmethod
    async def _render_agent_result(result: dict):
        """Display the final result from the agent."""
        if result.get("current_question") and result.get("question_approved"):
            await ChainlitHandler._render_question(result)
        elif result.get("messages"):
             last_content = result["messages"][-1].content
             await cl.Message(content=last_content).send()

    @staticmethod
    async def _render_question(result: dict):
        """Format and display a question with buttons."""
        # Retrieve the REGISTERED question data from the service
        # This ensures we display the exact shuffled order stored in the DB
        service = get_service()
        last_id = service.get_last_question_id()
        
        if not last_id:
             # Fallback if something failed (shouldn't happen if approved)
             q_text = result["current_question"]
             options = result["question_options"]
        else:
             q_data = service.get_question(last_id)
             q_text = q_data["question"]
             options = q_data["options"] # These are already shuffled
        
        question_display = f"**{q_text}**\n\n"
        actions = []
        for i, opt in enumerate(options):
            letter = chr(65+i)
            question_display += f"{letter}) {opt}\n"
            actions.append(cl.Action(
                name="answer", 
                payload={"value": letter}, 
                label=f"{letter}"
            ))
        
        await cl.Message(content=question_display, actions=actions).send()
