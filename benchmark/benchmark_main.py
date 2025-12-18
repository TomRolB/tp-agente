import argparse
import sys
import os
import time
from datetime import datetime
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.core.simulated_student import SimulatedStudent, ExpertPersona, NovicePersona, LearnerPersona
from benchmark.core.runner import BenchmarkRunner
from benchmark.reporting.data_serializer import BenchmarkDataSerializer


def parse_arguments():
    parser = argparse.ArgumentParser(description="Run Adaptive AI Benchmarking")
    parser.add_argument("--persona", type=str, choices=["expert", "novice", "learner"], required=True, 
                       help="Simulated student persona")
    parser.add_argument("--turns", type=int, default=10, help="Number of turns to simulate")
    parser.add_argument("--sleep", type=float, default=0, 
                       help="Sleep duration between turns in seconds (default: 0)")
    return parser.parse_args()


def create_benchmark_output_directory():
    """Create timestamped directory for benchmark output."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    benchmark_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(benchmark_dir, "reports", f"benchmark_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def save_benchmark_data(raw_data: dict, output_dir: str) -> str:
    """Save raw benchmark data to JSON file."""
    serializer = BenchmarkDataSerializer()
    data_path = os.path.join(output_dir, "data.json")
    serializer.save_to_file(raw_data, data_path)
    
    return data_path


def create_persona_from_name(persona_name):
    persona_map = {
        "expert": ExpertPersona,
        "novice": NovicePersona,
        "learner": LearnerPersona
    }
    return persona_map[persona_name]()


def execute_benchmark(persona, turns, sleep_duration) -> dict:
    student = SimulatedStudent(persona)
    runner = BenchmarkRunner(student, turns=turns, sleep_duration=sleep_duration)
    return runner.run()


def main():
    args = parse_arguments()

    output_dir = create_benchmark_output_directory()

    benchmark_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ["CONTENT_PATH"] = os.path.join(benchmark_dir, "content", "SD-Com.txt")
    
    print(f"Initializing benchmark for {args.persona} with {args.turns} turns...")
    
    persona = create_persona_from_name(args.persona)
    raw_data = execute_benchmark(persona, args.turns, args.sleep)
    
    data_path = save_benchmark_data(raw_data, output_dir)
    print(f"\nBenchmark data saved to {data_path}")
    print(f"To generate report, run: python generate_report.py {data_path}")

if __name__ == "__main__":
    main()

