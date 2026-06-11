"""Answer database models and speech/confidence data types."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SpeechMetrics(BaseModel):
    """Speech analysis metrics computed from a transcript."""

    wpm: int = Field(ge=0)
    total_words: int = Field(ge=0)
    filler_word_count: int = Field(ge=0)
    filler_words_detail: dict[str, int]
    speaking_duration: float = Field(gt=0)
    avg_pause_duration: float = Field(ge=0)
    communication_score: int = Field(ge=0, le=100)
    wpm_in_range: bool


class ConfidenceResult(BaseModel):
    """Confidence analysis result from speech patterns."""

    score: int = Field(ge=0, le=100)
    hesitation_count: int = Field(ge=0)
    pause_frequency: float = Field(ge=0)
    speech_flow_score: float = Field(ge=0, le=1)
    response_completeness: float = Field(ge=0, le=1)


class Answer(BaseModel):
    """Answer model matching the answers table schema."""

    id: UUID
    session_id: UUID
    question_index: int = Field(ge=0)
    question_text: str
    transcript: Optional[str] = None
    wpm: Optional[int] = Field(default=None, ge=0)
    total_words: Optional[int] = Field(default=None, ge=0)
    filler_word_count: Optional[int] = Field(default=None, ge=0)
    filler_words_detail: Optional[dict[str, int]] = None
    speaking_duration: Optional[float] = None
    avg_pause_duration: Optional[float] = None
    communication_score: Optional[int] = Field(default=None, ge=0, le=100)
    confidence_score: Optional[int] = Field(default=None, ge=0, le=100)
    ai_evaluation: Optional[dict[str, Any]] = None
    created_at: datetime


class AnswerCreate(BaseModel):
    """Schema for creating a new answer record."""

    session_id: UUID
    question_index: int = Field(ge=0)
    question_text: str
