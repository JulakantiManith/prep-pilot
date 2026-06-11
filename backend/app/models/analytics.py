"""Analytics and resume database models."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Resume(BaseModel):
    """Resume model matching the resumes table schema."""

    id: UUID
    user_id: UUID
    file_path: str
    file_name: str
    file_size: int = Field(ge=0)
    extracted_data: Optional[dict[str, Any]] = None
    extraction_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    user_confirmed: bool = False
    extraction_status: Optional[str] = None
    uploaded_at: datetime


class ResumeCreate(BaseModel):
    """Schema for creating a resume record."""

    user_id: UUID
    file_path: str
    file_name: str
    file_size: int = Field(ge=0)


class AnalyticsOverview(BaseModel):
    """Aggregated analytics data for the dashboard."""

    total_interview_sessions: int = Field(ge=0)
    total_presentation_sessions: int = Field(ge=0)
    average_overall_score: Optional[float] = Field(default=None, ge=0, le=100)
    latest_confidence_score: Optional[int] = Field(default=None, ge=0, le=100)
    latest_communication_score: Optional[int] = Field(default=None, ge=0, le=100)


class ScoreTrend(BaseModel):
    """A single data point in a score trend series."""

    date: str
    average_score: float = Field(ge=0, le=100)
    session_count: int = Field(ge=0)


class AnalyticsTrends(BaseModel):
    """Score trend data over a time period."""

    overall_scores: list[ScoreTrend] = Field(default_factory=list)
    confidence_scores: list[ScoreTrend] = Field(default_factory=list)
    communication_scores: list[ScoreTrend] = Field(default_factory=list)
