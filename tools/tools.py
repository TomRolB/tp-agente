from services.service import FileService
from services.service_manager import get_service
import os
import json


file_service = FileService()


def read_text_file(file_path: str) -> str:
    try:
        content = file_service.read_txt_file(file_path)
        return content
    except Exception as e:
        return f"Error al leer el archivo: {str(e)}"


def search_in_text_file(file_path: str, search_term: str,
                       case_sensitive: bool = False) -> str:
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


def check_multiple_choice_answer(question_id: str, user_answer: str) -> str:
    """Verifica si la respuesta del usuario es correcta y la almacena"""
    try:
        mcq_service = get_service()
        question_data = mcq_service.get_question(question_id)
        if not question_data:
            return f"Error: No se encontró pregunta con ID {question_id}"
        
        correct_answer = question_data["correct_answer"]
        options = question_data["options"]
        
        # Convertir respuesta de letra a texto si es necesario
        user_answer_text = user_answer
        if len(user_answer) == 1 and user_answer.upper() in 'ABCD':
            letter_index = ord(user_answer.upper()) - ord('A')
            if 0 <= letter_index < len(options):
                user_answer_text = options[letter_index]
        
        is_correct = user_answer_text == correct_answer
        
        mcq_service.store_user_answer(question_id, user_answer_text, is_correct)
        
        result = f"Respuesta registrada para pregunta {question_id}\n\n"
        result += f"Tu respuesta: {user_answer_text}\n"
        result += f"Respuesta correcta: {correct_answer}\n"
        result += f"Resultado: {'✓ CORRECTO' if is_correct else '✗ INCORRECTO'}"
        
        return result
        
    except Exception as e:
        return f"Error al verificar respuesta: {str(e)}"


def check_last_multiple_choice_answer(user_answer: str) -> str:
    """Verifica la respuesta del usuario contra la última pregunta creada"""
    try:
        mcq_service = get_service()
        last_id = mcq_service.get_last_question_id()
        if not last_id:
            return "Error: No hay preguntas registradas aún"
        return check_multiple_choice_answer(last_id, user_answer)
    except Exception as e:
        return f"Error al verificar respuesta para la última pregunta: {str(e)}"


def register_multiple_choice_question(question: str, options: list, correct_index: int) -> str:
    """Registra una pregunta de opción múltiple con 4 opciones y la respuesta correcta por índice (0-3)."""
    try:
        if not isinstance(options, list):
            return "Error: 'options' debe ser una lista de 4 strings"
        if len(options) != 4:
            return "Error: Deben proveerse exactamente 4 opciones"
        if not all(isinstance(opt, str) and opt.strip() for opt in options):
            return "Error: Todas las opciones deben ser strings no vacíos"
        if not isinstance(correct_index, int) or not (0 <= correct_index < 4):
            return "Error: 'correct_index' debe ser un entero entre 0 y 3"

        # Aleatorizar el orden de opciones para evitar sesgo (que no sea siempre sea la A, por ejemplo)
        import random
        indexed_options = list(enumerate(options))
        random.shuffle(indexed_options)
        shuffled_options = [opt for _, opt in indexed_options]
        # Calcular la nueva posición de la opción correcta tras mezclar
        original_correct_answer = options[correct_index]
        correct_answer = original_correct_answer
        mcq_service = get_service()
        question_id = mcq_service.store_question(question, shuffled_options, correct_answer)

        result = f"Pregunta registrada con ID: {question_id}\n\n"
        result += f"Pregunta: {question}\n\n"
        result += "Opciones:\n"
        for i, option in enumerate(shuffled_options, 1):
            result += f"{chr(64+i)}) {option}\n"

        return result
    except Exception as e:
        return f"Error al registrar pregunta: {str(e)}"


def list_multiple_choice_questions(limit: int = 20) -> str:
    """Lista las últimas preguntas registradas (sin revelar la respuesta correcta)"""
    try:
        mcq_service = get_service()
        all_questions = mcq_service.get_all_questions()
        items = list(all_questions.items())
        items.sort(key=lambda kv: kv[1].get("created_at"))
        if limit is not None:
            items = items[-limit:]
        lines = []
        for qid, data in items:
            question = data.get("question", "")
            options = data.get("options", [])
            # Formatear sin revelar la correcta
            lines.append(f"ID: {qid}\nPregunta: {question}\nOpciones:\n" + "\n".join(
                [f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)]
            ))
        return "\n\n".join(lines) if lines else "Sin preguntas registradas"
    except Exception as e:
        return f"Error al listar preguntas: {str(e)}"


def get_user_performance() -> str:
    """Obtiene el rendimiento y puntaje actual del usuario"""
    try:
        mcq_service = get_service()
        score_data = mcq_service.compute_user_score()
        
        if score_data['total_questions'] == 0:
            return "No hay respuestas registradas todavía. El usuario no ha respondido ninguna pregunta."
        
        result = f"=== RENDIMIENTO DEL USUARIO ===\n\n"
        result += f"Total de preguntas respondidas: {score_data['total_questions']}\n"
        result += f"Respuestas correctas: {score_data['correct_count']}\n"
        result += f"Respuestas incorrectas: {score_data['incorrect_count']}\n"
        result += f"Porcentaje de aciertos: {score_data['score_percentage']:.1f}%\n\n"
        
        if score_data['recent_performance']:
            result += "Rendimiento reciente (últimas 5 respuestas):\n"
            for i, perf in enumerate(score_data['recent_performance'], 1):
                status = "✓ CORRECTO" if perf['is_correct'] else "✗ INCORRECTO"
                result += f"  {i}. {status}\n"
        
        return result
    except Exception as e:
        return f"Error al obtener rendimiento: {str(e)}"


def get_answer_history_detailed() -> str:
    """Obtiene el historial detallado de respuestas del usuario"""
    try:
        mcq_service = get_service()
        history = mcq_service.get_answer_history()
        
        if not history:
            return "No hay historial de respuestas todavía."
        
        result = f"=== HISTORIAL DE RESPUESTAS ({len(history)} preguntas) ===\n\n"
        
        for i, entry in enumerate(history, 1):
            result += f"--- Pregunta {i} ---\n"
            result += f"Pregunta: {entry['question']}\n"
            result += f"Respuesta del usuario: {entry['user_answer']}\n"
            result += f"Respuesta correcta: {entry['correct_answer']}\n"
            result += f"Resultado: {'✓ CORRECTO' if entry['is_correct'] else '✗ INCORRECTO'}\n\n"
        
        return result
    except Exception as e:
        return f"Error al obtener historial: {str(e)}"

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_text_file",
            "description": "Lee el contenido completo de un archivo .txt",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Ruta completa al archivo .txt"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_text_file",
            "description": "Busca un término en un archivo .txt",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Ruta al archivo"
                    },
                    "search_term": {
                        "type": "string",
                        "description": "Término a buscar"
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Distinguir mayúsculas",
                        "default": False
                    }
                },
                "required": ["file_path", "search_term"]
            }
        }
    },
    
    {
        "type": "function",
        "function": {
            "name": "check_multiple_choice_answer",
            "description": "Verifica si la respuesta del usuario es correcta",
            "parameters": {
                "type": "object",
                "properties": {
                    "question_id": {
                        "type": "string",
                        "description": "ID de la pregunta"
                    },
                    "user_answer": {
                        "type": "string",
                        "description": "Respuesta del usuario (letra A-D o texto completo)"
                    }
                },
                "required": ["question_id", "user_answer"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_multiple_choice_questions",
            "description": "Lista las últimas preguntas registradas (sin revelar la respuesta correcta)",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Cantidad máxima a listar",
                        "default": 20
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_last_multiple_choice_answer",
            "description": "Verifica si la respuesta del usuario es correcta para la última pregunta creada",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_answer": {
                        "type": "string",
                        "description": "Respuesta del usuario (letra A-D o texto completo)"
                    }
                },
                "required": ["user_answer"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "register_multiple_choice_question",
            "description": "Registra una pregunta con 4 opciones y el índice correcto (0-3)",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Texto de la pregunta"
                    },
                    "options": {
                        "type": "array",
                        "description": "Arreglo de 4 opciones",
                        "items": {"type": "string"},
                        "minItems": 4,
                        "maxItems": 4
                    },
                    "correct_index": {
                        "type": "integer",
                        "description": "Índice de la opción correcta (0-3)",
                        "minimum": 0,
                        "maximum": 3
                    }
                },
                "required": ["question", "options", "correct_index"]
            }
        }
    }
]

TOOLS_MAP = {
    "read_text_file": read_text_file,
    "search_in_text_file": search_in_text_file,
    "check_multiple_choice_answer": check_multiple_choice_answer,
    "check_last_multiple_choice_answer": check_last_multiple_choice_answer,
    "register_multiple_choice_question": register_multiple_choice_question,
    "list_multiple_choice_questions": list_multiple_choice_questions
}
