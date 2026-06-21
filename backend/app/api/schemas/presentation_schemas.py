"""Pydantic schemas for presentation session API endpoints.

Defines request and response models for presentation session creation,
recording upload, materials upload, and session completion endpoints.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# --- Request Schemas ---


class CreatePresentationSessionRequest(BaseModel):
    """Request body for creating a new presentation session."""

    title: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional title for the presentation",
    )
    topic: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Topic of the presentation",
    )
    duration_estimate_minutes: Optional[int] = Field(
        default=5,
        ge=1,
        le=20,
        description="Estimated duration in minutes (1-20). Default: 5 minutes.",
    )


class CompletePresentationRequest(BaseModel):
    """Request body for completing a presentation session (extensible)."""

    pass


# --- Response Schemas ---


class PresentationSessionResponse(BaseModel):
    """Presentation session data in API responses."""

    id: UUID
    user_id: UUID
    session_type: str
    title: Optional[str] = None
    topic: Optional[str] = None
    overall_score: Optional[int] = None
    confidence_score: Optional[int] = None
    communication_score: Optional[int] = None
    duration_seconds: Optional[int] = None
    status: str
    recording_url: Optional[str] = None
    materials_url: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class CreatePresentationSessionResponse(BaseModel):
    """Response for presentation session creation endpoint."""

    session: PresentationSessionResponse


class UploadRecordingResponse(BaseModel):
    """Response for recording upload endpoint."""

    session_id: UUID
    recording_url: str
    message: str = "Recording uploaded successfully"


class UploadMaterialsResponse(BaseModel):
    """Response for materials upload endpoint."""

    session_id: UUID
    materials_url: str
    message: str = "Materials uploaded successfully"


class PresentationScoresResponse(BaseModel):
    """Presentation-specific scores breakdown."""

    speaking_speed: int = Field(ge=0, le=100)
    clarity: int = Field(ge=0, le=100)
    structure: int = Field(ge=0, le=100)
    communication: int = Field(ge=0, le=100)
    engagement: int = Field(ge=0, le=100)


class PresentationFeedbackResponse(BaseModel):
    """AI-generated feedback in presentation completion response."""

    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    presentation_scores: Optional[PresentationScoresResponse] = None


class CompletePresentationResponse(BaseModel):
    """Response for presentation session completion endpoint."""

    session: PresentationSessionResponse
    scores: Optional[PresentationScoresResponse] = None
    feedback: Optional[PresentationFeedbackResponse] = None
