import os
from typing import List, Dict, Optional
import uuid
from datetime import datetime


class MCQService:
    def __init__(self):
        self._questions: Dict[str, Dict] = {}
        self._answers: Dict[str, Dict] = {}
    
    def store_question(self, question: str, options: List[str], correct_answer: str) -> str:
        """Almacena una pregunta de opción múltiple y retorna su ID"""
        question_id = str(uuid.uuid4())
        self._questions[question_id] = {
            'question': question,
            'options': options,
            'correct_answer': correct_answer,
            'created_at': datetime.now()
        }
        return question_id
    
    def get_question(self, question_id: str) -> Optional[Dict]:
        """Obtiene una pregunta por su ID"""
        return self._questions.get(question_id)
    
    def store_user_answer(self, question_id: str, user_answer: str, is_correct: bool) -> bool:
        """Almacena la respuesta del usuario y si fue correcta"""
        if question_id not in self._questions:
            return False
        
        self._answers[question_id] = {
            'user_answer': user_answer,
            'is_correct': is_correct,
            'answered_at': datetime.now()
        }
        return True
    
    def get_user_answer(self, question_id: str) -> Optional[Dict]:
        """Obtiene la respuesta del usuario para una pregunta"""
        return self._answers.get(question_id)
    
    def get_all_questions(self) -> Dict[str, Dict]:
        """Obtiene todas las preguntas almacenadas"""
        return self._questions.copy()
    
    def get_all_answers(self) -> Dict[str, Dict]:
        """Obtiene todas las respuestas almacenadas"""
        return self._answers.copy()

    def get_last_question_id(self) -> Optional[str]:
        """Retorna el ID de la pregunta creada más recientemente"""
        if not self._questions:
            return None
        return max(self._questions.items(), key=lambda item: item[1].get('created_at'))[0]
    
    def compute_user_score(self) -> Dict:
        """Calcula el puntaje y métricas de rendimiento del usuario"""
        total_questions = len(self._answers)
        if total_questions == 0:
            return {
                'total_questions': 0,
                'correct_count': 0,
                'incorrect_count': 0,
                'score_percentage': 0.0,
                'recent_performance': []
            }
        
        correct_count = sum(1 for ans in self._answers.values() if ans['is_correct'])
        incorrect_count = total_questions - correct_count
        score_percentage = (correct_count / total_questions) * 100
        
        # Obtener las últimas 5 respuestas
        sorted_answers = sorted(
            self._answers.items(),
            key=lambda x: x[1]['answered_at']
        )
        recent_answers = sorted_answers[-5:]
        recent_performance = [
            {
                'question_id': qid,
                'is_correct': ans['is_correct'],
                'answered_at': ans['answered_at']
            }
            for qid, ans in recent_answers
        ]
        
        return {
            'total_questions': total_questions,
            'correct_count': correct_count,
            'incorrect_count': incorrect_count,
            'score_percentage': score_percentage,
            'recent_performance': recent_performance
        }
    
    def get_answer_history(self) -> List[Dict]:
        """Retorna historial cronológico de respuestas"""
        sorted_answers = sorted(
            self._answers.items(),
            key=lambda x: x[1]['answered_at']
        )
        
        history = []
        for qid, ans in sorted_answers:
            question_data = self._questions.get(qid, {})
            history.append({
                'question_id': qid,
                'question': question_data.get('question', ''),
                'user_answer': ans['user_answer'],
                'correct_answer': question_data.get('correct_answer', ''),
                'is_correct': ans['is_correct'],
                'answered_at': ans['answered_at']
            })
        
        return history


class FileService:
    @staticmethod
    def read_txt_file(file_path: str) -> str:
        if not file_path.endswith('.txt'):
            raise ValueError(f"El archivo debe tener extensión .txt: {file_path}")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def read_directory_content(directory_path: str) -> str:
        """Lee todos los archivos .txt de un directorio y los combina."""
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directorio no encontrado: {directory_path}")
        if not os.path.isdir(directory_path):
            raise ValueError(f"La ruta no es un directorio: {directory_path}")

        txt_files = [f for f in os.listdir(directory_path) if f.endswith('.txt')]

        if not txt_files:
            raise FileNotFoundError(f"No se encontraron archivos .txt en: {directory_path}")

        combined_content = []
        for file_name in sorted(txt_files):
            file_path = os.path.join(directory_path, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    combined_content.append(f"=== Contenido de {file_name} ===\n\n{content}\n\n")
            except Exception as e:
                combined_content.append(f"=== Error al leer {file_name}: {str(e)} ===\n\n")

        return "\n".join(combined_content)

    @staticmethod
    def search_in_file(file_path: str, search_term: str,
                      case_sensitive: bool = False) -> List[Dict[str, any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        results = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                line_to_search = line if case_sensitive else line.lower()
                term_to_search = search_term if case_sensitive else search_term.lower()
                if term_to_search in line_to_search:
                    results.append({
                        "line_number": line_num,
                        "content": line.strip(),
                        "file_path": file_path
                    })
        return results


class OpenEndedService:
    """Service for managing open-ended questions and evaluations."""

    def __init__(self):
        self._questions: Dict[str, Dict] = {}
        self._evaluations: Dict[str, Dict] = {}

    def store_question(self, question: str, criteria: str,
                      key_concepts: List[str], difficulty: str) -> str:
        """Almacena una pregunta abierta y retorna su ID"""
        question_id = str(uuid.uuid4())
        self._questions[question_id] = {
            'question': question,
            'evaluation_criteria': criteria,
            'key_concepts': key_concepts,
            'difficulty': difficulty,
            'created_at': datetime.now()
        }
        return question_id

    def get_question(self, question_id: str) -> Optional[Dict]:
        """Obtiene una pregunta por su ID"""
        return self._questions.get(question_id)

    def store_evaluation(self, question_id: str, user_answer: str,
                        score: float, feedback: str, is_passing: bool,
                        strengths: List[str], weaknesses: List[str]) -> bool:
        """Almacena la evaluación de una respuesta abierta"""
        if question_id not in self._questions:
            return False

        self._evaluations[question_id] = {
            'user_answer': user_answer,
            'score': score,
            'feedback': feedback,
            'is_passing': is_passing,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'evaluated_at': datetime.now()
        }
        return True

    def get_evaluation(self, question_id: str) -> Optional[Dict]:
        """Obtiene la evaluación para una pregunta"""
        return self._evaluations.get(question_id)

    def get_all_questions(self) -> Dict[str, Dict]:
        """Obtiene todas las preguntas almacenadas"""
        return self._questions.copy()

    def get_all_evaluations(self) -> Dict[str, Dict]:
        """Obtiene todas las evaluaciones almacenadas"""
        return self._evaluations.copy()

    def get_last_question_id(self) -> Optional[str]:
        """Retorna el ID de la pregunta creada más recientemente"""
        if not self._questions:
            return None
        return max(self._questions.items(), key=lambda item: item[1].get('created_at'))[0]

    def compute_user_score(self) -> Dict:
        """Calcula métricas de rendimiento para preguntas abiertas"""
        total_questions = len(self._evaluations)
        if total_questions == 0:
            return {
                'total_questions': 0,
                'avg_score': 0.0,
                'passing_count': 0,
                'score_percentage': 0.0,
                'recent_performance': []
            }

        scores = [eval_data['score'] for eval_data in self._evaluations.values()]
        avg_score = sum(scores) / len(scores)
        passing_count = sum(1 for eval_data in self._evaluations.values() if eval_data['is_passing'])
        score_percentage = (avg_score / 10.0) * 100  # Convert to percentage

        # Obtener las últimas 5 evaluaciones
        sorted_evals = sorted(
            self._evaluations.items(),
            key=lambda x: x[1]['evaluated_at']
        )
        recent_evals = sorted_evals[-5:]
        recent_performance = [
            {
                'question_id': qid,
                'score': eval_data['score'],
                'is_passing': eval_data['is_passing'],
                'evaluated_at': eval_data['evaluated_at']
            }
            for qid, eval_data in recent_evals
        ]

        return {
            'total_questions': total_questions,
            'avg_score': avg_score,
            'passing_count': passing_count,
            'score_percentage': score_percentage,
            'recent_performance': recent_performance
        }

    def get_evaluation_history(self) -> List[Dict]:
        """Retorna historial cronológico de evaluaciones"""
        sorted_evals = sorted(
            self._evaluations.items(),
            key=lambda x: x[1]['evaluated_at']
        )

        history = []
        for qid, eval_data in sorted_evals:
            question_data = self._questions.get(qid, {})
            history.append({
                'question_id': qid,
                'question': question_data.get('question', ''),
                'user_answer': eval_data['user_answer'],
                'score': eval_data['score'],
                'feedback': eval_data['feedback'],
                'is_passing': eval_data['is_passing'],
                'strengths': eval_data['strengths'],
                'weaknesses': eval_data['weaknesses'],
                'evaluated_at': eval_data['evaluated_at']
            })

        return history


class UnifiedPerformanceService:
    """Combina métricas de MCQ y Open-Ended"""

    def __init__(self, mcq_service: MCQService, open_service: OpenEndedService):
        self.mcq = mcq_service
        self.open = open_service

    def compute_unified_performance(self) -> Dict:
        """
        Retorna performance unificado combinando MCQ y Open-Ended.
        Usa peso proporcional basado en cantidad de preguntas de cada tipo.
        """
        mcq_data = self.mcq.compute_user_score()
        open_data = self.open.compute_user_score()

        mcq_count = mcq_data['total_questions']
        open_count = open_data['total_questions']
        total_qs = mcq_count + open_count

        if total_qs == 0:
            return {
                'overall_percentage': 0.0,
                'mcq_percentage': 0.0,
                'open_percentage': 0.0,
                'total_questions': 0,
                'mcq_count': 0,
                'open_count': 0,
                'mcq_correct': 0,
                'open_avg_score': 0.0,
                'recent_overall_performance': []
            }

        # Usar peso proporcional
        mcq_percentage = mcq_data['score_percentage']
        open_percentage = open_data['score_percentage']

        if mcq_count > 0 and open_count > 0:
            mcq_weight = mcq_count / total_qs
            open_weight = open_count / total_qs
            overall_percentage = (mcq_percentage * mcq_weight) + (open_percentage * open_weight)
        elif mcq_count > 0:
            overall_percentage = mcq_percentage
        else:
            overall_percentage = open_percentage

        # Combinar performance reciente de ambos tipos
        recent_combined = []

        # Agregar performance MCQ reciente
        for perf in mcq_data['recent_performance']:
            recent_combined.append({
                'type': 'mcq',
                'question_id': perf['question_id'],
                'is_correct': perf['is_correct'],
                'score': None,
                'timestamp': perf['answered_at']
            })

        # Agregar performance Open-Ended reciente
        for perf in open_data['recent_performance']:
            recent_combined.append({
                'type': 'open_ended',
                'question_id': perf['question_id'],
                'is_correct': None,
                'score': perf['score'],
                'timestamp': perf['evaluated_at']
            })

        # Ordenar por timestamp y tomar las últimas 5
        recent_combined.sort(key=lambda x: x['timestamp'])
        recent_overall_performance = recent_combined[-5:]

        return {
            'overall_percentage': overall_percentage,
            'mcq_percentage': mcq_percentage,
            'open_percentage': open_percentage,
            'total_questions': total_qs,
            'mcq_count': mcq_count,
            'open_count': open_count,
            'mcq_correct': mcq_data['correct_count'],
            'open_avg_score': open_data['avg_score'],
            'recent_overall_performance': recent_overall_performance
        }