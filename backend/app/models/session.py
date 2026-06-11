"""Session database models and enums."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SessionType(str, Enum):
    """Type of practice session."""

    INTERVIEW = "interview"
    PRESENTATION = "presentation"


class InterviewType(str, Enum):
    """Type of interview session."""

    HR = "hr"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    CUSTOM = "custom"
    RESUME_BASED = "resume_based"


class Difficulty(str, Enum):
    """Difficulty level for interview questions."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class SessionStatus(str, Enum):
    """Status of a session."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Session(BaseModel):
    """Session model matching the sessions table schema."""

    id: UUID
    user_id: UUID
    session_type: SessionType
    interview_type: Optional[InterviewType] = None
    role: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    overall_score: Optional[int] = Field(default=None, ge=0, le=100)
    confidence_score: Optional[int] = Field(default=None, ge=0, le=100)
    communication_score: Optional[int] = Field(default=None, ge=0, le=100)
    duration_seconds: Optional[int] = None
    status: SessionStatus = SessionStatus.IN_PROGRESS
    created_at: datetime
    completed_at: Optional[datetime] = None


class SessionCreate(BaseModel):
    """Schema for creating a new session."""

    session_type: SessionType
    interview_type: Optional[InterviewType] = None
    role: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[Difficulty] = None
