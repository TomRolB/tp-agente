# Adaptive Learning Agent

This project implements an intelligent multi-agent system designed to deliver adaptive educational content. It uses a graph-based agent architecture (LangGraph) to generate questions, evaluate student answers, and adapt the difficulty level based on performance, simulating a personalized tutoring experience.

## Benchmarking

The project includes a robust benchmarking suite designed to rigorously evaluate the system's pedagogical capabilities. The goal is to ensure the agent correctly adapts to different student levels and adequately covers the provided curriculum.

### How It Works

The benchmark simulates a learning session by replacing the human user with a **Simulated Student Persona**. This persona is an LLM configured with specific cognitive traits and knowledge levels. The system and the persona interact in a loop:

1.  **System** generates a question based on current difficulty and history.
2.  **Persona** answers the question based on its profile.
3.  **System** evaluates the answer and adjusts difficulty.
4.  **Benchmark** records all interactions, metrics, and syllabus coverage.

### Personas

We test against two distinct profiles to validate adaptivity:
*   **Novice**: Makes frequent mistakes, especially on complex topics. Tests if the system lowers difficulty and offers remediation.
*   **Expert**: Consistently answers correctly. Tests if the system raises difficulty to challenge the user.

### Running a Benchmark

The process is decoupled into **execution** and **reporting** to allow for data inspection and manual adjustment if needed.

**1. Execute the Benchmark**
Runs the simulation and saves raw data (JSON) to `benchmark/reports/`.
```bash
# Run 15 turns with an Expert persona
python -m benchmark.benchmark_main --persona Expert --turns 15
```
*Arguments: `--persona` (Expert/Novice), `--turns` (number of questions).*

**2. Generate the Report**
Reads the raw data and creates a comprehensive Markdown report with visualization matrices and scored metrics.
```bash
python benchmark/generate_report.py benchmark/reports/<timestamp_folder>/data.json
```

### Key Metrics
The report evaluates the system on:
*   **Effective Curriculum Coverage (ECC)**: Measures the system's effectiveness in guiding the student to master the full syllabus, rewarding broad topic coverage over repetition.
*   **Remediation Efficiency**: How well the system recovers after a student makes a mistake.
*   **Difficulty-Weighted Proficiency**: Evaluates if the system maintains the student in the "optimal learning zone" (neither bored nor overwhelmed).
*   **Error Sensitivity**: Whether the system reacts appropriately (drops difficulty) when errors occur.

These metrics are weighted and aggregated into a **Final Score** to provide a single, overall quality assessment of the adaptive session.
