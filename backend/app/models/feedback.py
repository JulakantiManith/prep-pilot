"""Feedback database models and report data types."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PresentationScores(BaseModel):
    """Presentation-specific scoring breakdown."""

    speaking_speed: int = Field(ge=0, le=100)
    clarity: int = Field(ge=0, le=100)
    structure: int = Field(ge=0, le=100)
    communication: int = Field(ge=0, le=100)
    engagement: int = Field(ge=0, le=100)


class FeedbackReport(BaseModel):
    """AI-generated feedback report for a session."""

    strengths: list[str] = Field(min_length=2)
    weaknesses: list[str] = Field(min_length=2)
    recommendations: list[str] = Field(min_length=3)
    technical_evaluation: Optional[dict[str, Any]] = None
    presentation_scores: Optional[PresentationScores] = None


class SessionFeedback(BaseModel):
    """Session feedback model matching the session_feedback table schema."""

    id: UUID
    session_id: UUID
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    technical_evaluation: Optional[dict[str, Any]] = None
    presentation_scores: Optional[dict[str, Any]] = None
    created_at: datetime


class SessionFeedbackCreate(BaseModel):
    """Schema for creating session feedback."""

    session_id: UUID
    strengths: list[str] = Field(min_length=2)
    weaknesses: list[str] = Field(min_length=2)
    recommendations: list[str] = Field(min_length=3)
    technical_evaluation: Optional[dict[str, Any]] = None
    presentation_scores: Optional[dict[str, Any]] = None
