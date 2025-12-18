"""Data models for multi-agent system."""

from typing import TypedDict, Annotated
from enum import Enum
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class QuestionType(str, Enum):
    """Enum for question types."""
    MCQ = "mcq"
    OPEN_ENDED = "open_ended"


class QuestionOutput(BaseModel):
    """Question Creator output schema."""
    question: str = Field(description="Question text")
    options: list[str] = Field(description="4 answer options")
    correct_index: int = Field(description="Correct answer index (0-3)", ge=0, le=3)


class OpenEndedQuestionOutput(BaseModel):
    """Open-Ended Question Creator output schema."""
    question: str = Field(description="Open-ended question text")
    evaluation_criteria: str = Field(description="Evaluation criteria or model answer")
    key_concepts: list[str] = Field(description="Key concepts expected in answer")
    difficulty_level: str = Field(description="Expected difficulty: easy/moderate/hard")


class OpenEndedEvaluationOutput(BaseModel):
    """Open-Ended Answer Evaluator output schema."""
    score: float = Field(description="Score from 0.0 to 10.0", ge=0.0, le=10.0)
    feedback: str = Field(description="Detailed textual feedback")
    is_passing: bool = Field(description="Whether score >= 7.0")
    strengths: list[str] = Field(description="Strong points in the answer")
    weaknesses: list[str] = Field(description="Areas for improvement")


class DifficultyReviewOutput(BaseModel):
    """Difficulty Reviewer output schema."""
    approved: bool = Field(description="Whether question is approved")
    feedback: str = Field(description="Review feedback")


class AgentState(TypedDict):
    """Shared state for multi-agent workflow."""
    messages: Annotated[list, add_messages]

    # Common fields
    question_type: str
    next_action: str
    difficulty_feedback: str
    user_feedback: str
    score_data: dict
    iteration_count: int
    question_approved: bool
    question_type_decision: str
    question_id: str

    # MCQ-specific fields
    current_question: str
    question_options: list
    question_correct_index: int

    # Open-ended specific fields
    open_question: str
    open_evaluation_criteria: str
    open_key_concepts: list
    open_question_difficulty: str

    # For evaluation workflow
    user_open_answer: str
    evaluation_score: float
    evaluation_feedback: str
    evaluation_passing: bool
