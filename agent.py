from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
import os
from services.service import FileService, MCQService
from tools.tools import check_multiple_choice_answer as check_answer_func
from tools.tools import check_last_multiple_choice_answer as check_last_answer_func
from tools.tools import register_multiple_choice_question as register_mcq_func
from tools.tools import list_multiple_choice_questions as list_mcqs_func

load_dotenv()

file_service = FileService()
mcq_service = MCQService()


@tool
def read_text_file(file_path: str) -> str:
    """Lee el contenido completo de un archivo .txt"""
    try:
        return file_service.read_txt_file(file_path)
    except Exception as e:
        return f"Error al leer el archivo: {str(e)}"


@tool
def search_in_text_file(file_path: str, search_term: str, case_sensitive: bool = False) -> str:
    """Busca un término en un archivo .txt"""
    try:
        results = file_service.search_in_file(file_path, search_term, case_sensitive)
        if not results:
            return f"No se encontraron resultados para '{search_term}' en el archivo."
        output = f"Encontrados {len(results)} resultados para '{search_term}':\n\n"
        for result in results:
            output += f"Línea {result['line_number']}: {result['content']}\n"
        return output
    except Exception as e:
        return f"Error en búsqueda: {str(e)}"


@tool
def check_multiple_choice_answer(question_id: str, user_answer: str) -> str:
    """Verifica si la respuesta del usuario es correcta y la almacena"""
    return check_answer_func(question_id, user_answer)


@tool
def register_multiple_choice_question(question: str, options: list, correct_index: int) -> str:
    """Registra una pregunta con 4 opciones y el índice correcto (0-3)"""
    return register_mcq_func(question, options, correct_index)

@tool
def check_last_multiple_choice_answer(user_answer: str) -> str:
    """Verifica la respuesta del usuario para la última pregunta creada"""
    return check_last_answer_func(user_answer)

@tool
def list_multiple_choice_questions(limit: int = 20) -> str:
    """Lista las últimas preguntas registradas (sin revelar la respuesta correcta)"""
    return list_mcqs_func(limit)


tools = [
    read_text_file,
    search_in_text_file,
    check_multiple_choice_answer,
    check_last_multiple_choice_answer,
    register_multiple_choice_question,
    list_multiple_choice_questions,
]

if __name__ == "__main__":
    # Get content directory from env
    content_dir = os.environ.get("CONTENT_DIR", "./content")

    agent = create_react_agent(
        model="openai:gpt-4o-mini",
        tools=tools,
        prompt="Eres un asistente que puede leer y buscar en archivos .txt, y crear preguntas de opción múltiple. Ayuda al usuario a procesar archivos de texto y crear evaluaciones. Las preguntas deben ser nuevas; comprobá las existentes y evita repetir."
    )

    print("=" * 60)
    print("EJEMPLO 1: Leer archivos del directorio de contenido")
    print("=" * 60)

    result = agent.invoke({
        "messages": [{"role": "user", "content": f"Lee los archivos de {content_dir} y dame un resumen"}]
    })
    print(f"\nRespuesta: {result['messages'][-1].content}\n")

    print("=" * 60)
    print("EJEMPLO 2: Crear y registrar MCQ basado en el contenido")
    print("=" * 60)

    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": f"Lee los archivos de {content_dir} y crea una pregunta de opción múltiple nueva basada en su contenido."
        }]
    })
    print(f"\nRespuesta: {result['messages'][-1].content}\n")
    
    print("=" * 60)
    print("EJEMPLO 3: Responder a la pregunta de opción múltiple (1)")
    print("=" * 60)

    user_answer_message = "La respuesta es la B para la última pregunta creada"
    print(f"Usuario: {user_answer_message}")
    result = agent.invoke({
        "messages": [{"role": "user", "content": user_answer_message}]
    })
    print(f"\nRespuesta: {result['messages'][-1].content}\n")

    print("=" * 60)
    print("EJEMPLO 4: Crear y registrar una segunda MCQ (el asistente evita repetir)")
    print("=" * 60)

    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": f"Crea otra pregunta de opción múltiple nueva basada en el contenido de {content_dir}."
        }]
    })
    print(f"\nRespuesta: {result['messages'][-1].content}\n")

    print("=" * 60)
    print("EJEMPLO 5: Responder a la pregunta de opción múltiple (2)")
    print("=" * 60)

    user_answer_message = "La respuesta es la B para la última pregunta creada"
    print(f"Usuario: {user_answer_message}")
    result = agent.invoke({
        "messages": [{"role": "user", "content": user_answer_message}]
    })
    print(f"\nRespuesta: {result['messages'][-1].content}\n")

    print("=" * 60)
    print("EJEMPLO 6: Crear y registrar una tercera MCQ (el asistente evita repetir)")
    print("=" * 60)

    result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": f"Crea una tercera pregunta de opción múltiple nueva basada en el contenido de {content_dir}."
        }]
    })
    print(f"\nRespuesta: {result['messages'][-1].content}\n")

    print("=" * 60)
    print("EJEMPLO 7: Responder a la pregunta de opción múltiple (3)")
    print("=" * 60)

    user_answer_message = "La respuesta es la B para la última pregunta creada"
    print(f"Usuario: {user_answer_message}")
    result = agent.invoke({
        "messages": [{"role": "user", "content": user_answer_message}]
    })
    print(f"\nRespuesta: {result['messages'][-1].content}\n")
