"""Pydantic schemas for interview session API endpoints.

Defines request and response models for session creation,
answer submission, and session completion endpoints.
"""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.session import Difficulty, InterviewType


# --- Request Schemas ---


class CreateSessionRequest(BaseModel):
    """Request body for creating a new interview session."""

    interview_type: InterviewType = Field(
        ..., description="Type of interview (hr, technical, behavioral, custom)"
    )
    role: str = Field(
        ..., min_length=1, max_length=200, description="Target job role"
    )
    topic: Optional[str] = Field(
        default=None, max_length=200, description="Optional topic for technical interviews"
    )
    difficulty: Optional[Difficulty] = Field(
        default=None, description="Optional difficulty level"
    )
    num_questions: int = Field(
        default=5, ge=1, le=20, description="Number of questions to generate"
    )


class CompleteSessionRequest(BaseModel):
    """Request body for completing a session (currently empty, extensible)."""

    pass


# --- Response Schemas ---


class QuestionResponse(BaseModel):
    """Question data in API responses."""

    text: str
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    interview_type: Optional[str] = None
    follow_up: Optional[str] = None


class SessionResponse(BaseModel):
    """Session data in API responses."""

    id: UUID
    user_id: UUID
    session_type: str
    interview_type: Optional[str] = None
    role: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    overall_score: Optional[int] = None
    confidence_score: Optional[int] = None
    communication_score: Optional[int] = None
    duration_seconds: Optional[int] = None
    status: str
    created_at: str
    completed_at: Optional[str] = None


class CreateSessionResponse(BaseModel):
    """Response for session creation endpoint."""

    session: SessionResponse
    questions: list[QuestionResponse]
    question_source: str = Field(
        description="Source of questions: 'gemini', 'cache', or 'fallback'"
    )
    fallback_used: bool = Field(
        description="Whether fallback question bank was used"
    )


class AnswerResponse(BaseModel):
    """Answer data in API responses."""

    id: UUID
    session_id: UUID
    question_index: int
    question_text: str
    transcript: Optional[str] = None
    wpm: Optional[int] = None
    total_words: Optional[int] = None
    filler_word_count: Optional[int] = None
    communication_score: Optional[int] = None
    confidence_score: Optional[int] = None
    created_at: str


class SubmitAnswerResponse(BaseModel):
    """Response for answer submission endpoint."""

    answer: AnswerResponse
    transcript: str = Field(
        description="Raw transcript exactly as returned by the speech-to-text provider"
    )
    is_meaningful: bool = Field(
        default=True,
        description=(
            "Whether the transcript contains meaningful speech content. "
            "False indicates the audio was silent or contained only filler words "
            "(likely STT hallucination from silence/noise)."
        ),
    )


class ScoreSummary(BaseModel):
    """Aggregate score summary for a completed session."""

    overall_score: Optional[int] = None
    confidence_score: Optional[int] = None
    communication_score: Optional[int] = None


class FeedbackResponse(BaseModel):
    """AI-generated feedback in session completion response."""

    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    technical_evaluation: Optional[dict[str, Any]] = None


class CompleteSessionResponse(BaseModel):
    """Response for session completion endpoint."""

    session: SessionResponse
    total_answers: int
    scores: ScoreSummary
    feedback: Optional[FeedbackResponse] = None
