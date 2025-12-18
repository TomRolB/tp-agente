import time
from typing import Dict, List, Any
from unittest.mock import MagicMock, patch
from tqdm import tqdm

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from final.models import AgentState
from final.nodes import (
    question_creator_node,
    difficulty_reviewer_node,
    feedback_agent_node,
    orchestrator_node,
    present_question_node,
    route_orchestrator,
    route_after_feedback,
    route_after_question_creation,
    route_after_difficulty_review
)
from benchmark.core.simulated_student import SimulatedStudent
from benchmark.core.evaluator import BenchmarkEvaluator
from benchmark.core.topic_labeler import TopicLabeler

class BenchmarkRunner:
    def __init__(self, student: SimulatedStudent, turns: int = 10, sleep_duration: float = 0):
        self.student = student
        self.turns = turns
        self.sleep_duration = sleep_duration
        self.evaluator = BenchmarkEvaluator()
        self.topic_labeler = TopicLabeler()
        self.results: List[Dict[str, Any]] = []
        
        # We need a custom graph for benchmarking that mimics the real one
        # but intercepts the "end" state to loop back if needed,
        # or we just run the graph per turn.
        # Running per turn is safer to control the loop and injection.
        self.workflow = self._build_workflow()
        
    def _build_workflow(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("orchestrator", orchestrator_node)
        workflow.add_node("get_feedback", feedback_agent_node)
        workflow.add_node("create_mcq_question", question_creator_node)
        workflow.add_node("create_open_question", question_creator_node)
        workflow.add_node("review_difficulty", difficulty_reviewer_node)
        workflow.add_node("present_question", present_question_node)

        workflow.set_entry_point("orchestrator")

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
                "create_mcq_question": "create_mcq_question",
                "create_open_question": "create_open_question"
            }
        )

        workflow.add_conditional_edges(
            "create_open_question",
            route_after_question_creation,
            {
                "review_difficulty": "review_difficulty",
                "create_mcq_question": "create_mcq_question",
                "create_open_question": "create_open_question"
            }
        )

        workflow.add_conditional_edges(
            "review_difficulty",
            route_after_difficulty_review,
            {
                "present_question": "present_question",
                "create_mcq_question": "create_mcq_question",
                "create_open_question": "create_open_question"
            }
        )

        workflow.add_edge("present_question", END)

        return workflow.compile()

    def run(self) -> Dict:
        """Runs the benchmark and returns raw results data."""
        print(f"Starting benchmark for persona: {self.student.persona.__class__.__name__} with {self.turns} turns.")

        with patch('final.nodes.get_service') as mock_get_service, \
             patch('final.nodes.get_open_service') as mock_get_open_service, \
             patch('final.nodes.get_unified_perf_service') as mock_get_unified_perf:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service
            mock_get_open_service.return_value = MagicMock()

            mock_unified_perf_service = MagicMock()
            mock_unified_perf_service.compute_unified_performance.return_value = {
                'overall_percentage': 0.0,
                'total_questions': 0,
                'mcq_count': 0,
                'mcq_correct': 0,
                'mcq_percentage': 0.0,
                'open_count': 0,
                'open_avg_score': 0.0,
                'open_percentage': 0.0,
                'recent_overall_performance': []
            }
            mock_get_unified_perf.return_value = mock_unified_perf_service

            self._run_benchmark_loop(mock_service, mock_unified_perf_service)

        return self._prepare_raw_results()

    def _run_benchmark_loop(self, mock_service, mock_unified_perf_service):
        self._setup_initial_mock_state(mock_service)
        history = []
        state = self._get_initial_state()

        for turn in range(1, self.turns + 1):
            print(f"--- Turn {turn}/{self.turns} ---")

            state, success = self._execute_single_turn(turn, state, history, mock_service, mock_unified_perf_service)
            if not success:
                break

    def _execute_single_turn(self, turn: int, state: Dict, history: List, mock_service, mock_unified_perf_service) -> tuple[Dict, bool]:
        self._update_mock_service(mock_service, history, mock_unified_perf_service)

        try:
            start_time = time.time()
            result = self.workflow.invoke(state)
            generation_time = time.time() - start_time

            turn_result = self._process_turn_result(result, turn, generation_time)

            if turn_result:
                history.append({
                    'is_correct': turn_result['is_correct'],
                    'answered_at': time.time()
                })
                self.results.append(turn_result)
            
            next_state = self._get_next_turn_state()
            
            if self.sleep_duration > 0 and turn < self.turns:
                self._sleep_with_progress(turn)
                
            return next_state, True
            
        except Exception as e:
            print(f"Error in turn {turn}: {e}")
            return state, False

    def _setup_initial_mock_state(self, mock_service):
        mock_service.compute_user_score.return_value = {
            'total_questions': 0,
            'correct_count': 0,
            'incorrect_count': 0,
            'score_percentage': 0.0,
            'recent_performance': []
        }

    def _get_initial_state(self):
        return {
            "messages": [HumanMessage(content="Quiero una pregunta nueva")],
            "iteration_count": 0,
            "score_data": {}
        }

    def _get_next_turn_state(self):
        return {
            "messages": [HumanMessage(content="Dame otra pregunta")],
            "iteration_count": 0,
        }

    def _process_turn_result(self, result: Dict, turn: int, generation_time: float) -> Dict[str, Any]:
        question = result.get("current_question")
        options = result.get("question_options")
        correct_idx = result.get("question_correct_index")
        
        if not question or not options:
            print("Error: No question generated in this turn.")
            return None
        
        difficulty_score = self.evaluator.evaluate_difficulty(question, options)
        subtopic_ids = self.topic_labeler.label_question(question, options)
        student_answer_letter = self.student.answer_question(question, options)
        
        letter_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
        student_idx = letter_map.get(student_answer_letter, -1)
        is_correct = (student_idx == correct_idx)
        
        return {
            "turn": turn,
            "question": question,
            "options": options,
            "difficulty_score": difficulty_score,
            "subtopics": subtopic_ids,
            "is_correct": is_correct,
            "student_answer": student_answer_letter,
            "correct_answer": chr(65 + correct_idx),
            "generation_time_seconds": round(generation_time, 2)
        }

    def _update_mock_service(self, mock_service, history, mock_unified_perf_service):
        total = len(history)
        correct = sum(1 for h in history if h['is_correct']) if total > 0 else 0
        incorrect = total - correct
        percentage = (correct / total) * 100 if total > 0 else 0
        recent = history[-5:]

        mock_service.compute_user_score.return_value = {
            'total_questions': total,
            'correct_count': correct,
            'incorrect_count': incorrect,
            'score_percentage': percentage,
            'recent_performance': recent
        }

        mock_service.get_last_question_id.return_value = "mock_id"

        recent_performance_formatted = [
            {'type': 'mcq', 'is_correct': h['is_correct']}
            for h in recent
        ]

        mock_unified_perf_service.compute_unified_performance.return_value = {
            'overall_percentage': percentage,
            'total_questions': total,
            'mcq_count': total,
            'mcq_correct': correct,
            'mcq_percentage': percentage,
            'open_count': 0,
            'open_avg_score': 0.0,
            'open_percentage': 0.0,
            'recent_overall_performance': recent_performance_formatted
        }

    def _sleep_with_progress(self, current_turn: int):
        """Sleep between turns with progress indicator."""
        print(f"\n⏳ Rate limit protection: Waiting {self.sleep_duration}s before next turn...")
        
        for _ in tqdm(range(int(self.sleep_duration * 10)), desc="Sleeping", unit="0.1s", ncols=80):
            time.sleep(0.1)
        
        print()

    def _prepare_raw_results(self) -> Dict:
        """Prepare raw results for serialization."""
        generation_times = [r['generation_time_seconds'] for r in self.results if 'generation_time_seconds' in r]

        timing_stats = {}
        if generation_times:
            timing_stats = {
                'average_generation_time_seconds': round(sum(generation_times) / len(generation_times), 2),
                'min_generation_time_seconds': round(min(generation_times), 2),
                'max_generation_time_seconds': round(max(generation_times), 2),
                'total_generation_time_seconds': round(sum(generation_times), 2)
            }

        return {
            'metadata': {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'turns_planned': self.turns,
                'turns_completed': len(self.results),
                'persona_type': self.student.persona.__class__.__name__,
                **timing_stats
            },
            'persona_config': {
                'true_level': self.student.persona.true_level,
                'target_sensitivity': self.student.persona.target_sensitivity,
                'target_accuracy': self.student.persona.target_accuracy
            },
            'results': self.results
        }

