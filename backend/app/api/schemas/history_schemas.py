"""Pydantic schemas for session history endpoints."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SessionListItem(BaseModel):
    """A single session entry in the history list."""

    id: str = Field(description="Session UUID")
    session_type: str = Field(description="Type of session (interview or presentation)")
    created_at: str = Field(description="Session date in ISO format")
    duration_seconds: Optional[int] = Field(
        default=None, description="Session duration in seconds"
    )
    overall_score: Optional[int] = Field(
        default=None, description="Overall performance score (0-100)"
    )
    status: str = Field(
        default="completed",
        description="Session status: completed, processing, or failed",
    )


class SessionHistoryListResponse(BaseModel):
    """Response schema for the paginated session history list endpoint.

    Requirements: 12.1, 12.2, 12.4, 12.5
    """

    sessions: list[SessionListItem] = Field(
        default_factory=list, description="List of session entries for the current page"
    )
    total_count: int = Field(
        ge=0, description="Total number of sessions matching filters"
    )
    total_pages: int = Field(ge=0, description="Total number of pages available")
    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, description="Number of sessions per page")


class AnswerDetail(BaseModel):
    """Full detail of a single answer within a session."""

    question_index: int
    question_text: Optional[str] = None
    transcript: Optional[str] = None
    wpm: Optional[float] = None
    total_words: Optional[int] = None
    filler_word_count: Optional[int] = None
    filler_words_detail: Optional[Any] = None
    speaking_duration: Optional[float] = None
    avg_pause_duration: Optional[float] = None
    communication_score: Optional[int] = None
    confidence_score: Optional[int] = None
    ai_evaluation: Optional[Any] = None
    created_at: Optional[str] = None


class SessionFeedbackDetail(BaseModel):
    """AI-generated feedback for a session."""

    strengths: Optional[list[str]] = None
    weaknesses: Optional[list[str]] = None
    recommendations: Optional[list[str]] = None
    technical_evaluation: Optional[Any] = None
    presentation_scores: Optional[Any] = None


class SessionDetailResponse(BaseModel):
    """Response schema for the full session detail endpoint.

    Requirements: 12.3
    """

    id: str = Field(description="Session UUID")
    session_type: str = Field(description="Type of session")
    interview_type: Optional[str] = Field(
        default=None, description="Interview sub-type (hr, technical, behavioral, custom)"
    )
    role: Optional[str] = Field(default=None, description="Target role for the session")
    topic: Optional[str] = Field(default=None, description="Session topic")
    difficulty: Optional[str] = Field(default=None, description="Difficulty level")
    overall_score: Optional[int] = Field(
        default=None, description="Overall performance score"
    )
    confidence_score: Optional[int] = Field(
        default=None, description="Confidence score"
    )
    communication_score: Optional[int] = Field(
        default=None, description="Communication score"
    )
    duration_seconds: Optional[int] = Field(
        default=None, description="Session duration in seconds"
    )
    status: Optional[str] = Field(default=None, description="Session status")
    created_at: str = Field(description="Session creation timestamp")
    completed_at: Optional[str] = Field(
        default=None, description="Session completion timestamp"
    )
    answers: list[AnswerDetail] = Field(
        default_factory=list, description="Full transcript with all answer details"
    )
    feedback: Optional[SessionFeedbackDetail] = Field(
        default=None, description="AI-generated session feedback"
    )
