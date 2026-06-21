"""Presentation session API routes.

Provides endpoints for creating presentation sessions, uploading recordings
and materials, and completing sessions with presentation-specific analysis.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

import logging
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.schemas.presentation_schemas import (
    CompletePresentationResponse,
    CreatePresentationSessionRequest,
    CreatePresentationSessionResponse,
    PresentationFeedbackResponse,
    PresentationScoresResponse,
    PresentationSessionResponse,
    UploadMaterialsResponse,
    UploadRecordingResponse,
)
from app.dependencies import CurrentUserDep
from app.services.presentation_service import (
    PresentationNotFoundError,
    PresentationService,
    PresentationServiceError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions/presentation", tags=["Presentation Sessions"])


def _get_presentation_service() -> PresentationService:
    """Get a PresentationService instance."""
    return PresentationService()


def _session_to_response(session: dict) -> PresentationSessionResponse:
    """Convert a session dict from the database to a response model.

    Args:
        session: Raw session dict from the repository.

    Returns:
        PresentationSessionResponse model.
    """
    return PresentationSessionResponse(
        id=session["id"],
        user_id=session["user_id"],
        session_type=session.get("session_type", "presentation"),
        title=session.get("role"),
        topic=session.get("topic"),
        overall_score=session.get("overall_score"),
        confidence_score=session.get("confidence_score"),
        communication_score=session.get("communication_score"),
        duration_seconds=session.get("duration_seconds"),
        status=session.get("status", "in_progress"),
        recording_url=None,
        materials_url=None,
        created_at=session.get("created_at", ""),
        completed_at=session.get("completed_at"),
    )


@router.post(
    "",
    response_model=CreatePresentationSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new presentation session",
)
async def create_presentation_session(
    request: CreatePresentationSessionRequest,
    current_user_id: CurrentUserDep,
):
    """Create a new presentation session.

    Initializes a presentation session that can receive recordings
    and materials for analysis.
    """
    service = _get_presentation_service()

    try:
        session = service.create_session(
            user_id=current_user_id,
            title=request.title,
            topic=request.topic,
            duration_estimate_minutes=request.duration_estimate_minutes,
        )
    except PresentationServiceError as e:
        logger.error("Failed to create presentation session: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create presentation session: {e}",
        )

    return CreatePresentationSessionResponse(
        session=_session_to_response(session),
    )


@router.post(
    "/{session_id}/recording",
    response_model=UploadRecordingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload presentation recording",
)
async def upload_recording(
    session_id: UUID,
    current_user_id: CurrentUserDep,
    recording: UploadFile = File(
        ..., description="Audio/video recording of the presentation"
    ),
):
    """Upload an audio or video recording for a presentation session.

    Activates recording storage and associates it with the session.
    Maximum recording size: 25 MB (~20 min of webm audio/video).
    Requirement 7.1: Activate audio and video recording simultaneously.
    """
    # Max 25 MB recording (supports ~20 min webm, aligns with Groq Whisper limit)
    MAX_RECORDING_SIZE = 25 * 1024 * 1024

    audio_data = await recording.read()

    if not audio_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recording file is empty",
        )

    if len(audio_data) > MAX_RECORDING_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Recording file is too large ({len(audio_data) // (1024 * 1024)} MB). "
                f"Maximum allowed size is 25 MB (~20 minutes of recording)."
            ),
        )

    filename = recording.filename or "recording.webm"
    service = _get_presentation_service()

    try:
        recording_url = await service.upload_recording(
            user_id=current_user_id,
            session_id=session_id,
            audio_data=audio_data,
            filename=filename,
        )
    except PresentationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Presentation session not found or access denied",
        )
    except PresentationServiceError as e:
        logger.error("Failed to upload recording: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload recording. Please try again.",
        )

    return UploadRecordingResponse(
        session_id=session_id,
        recording_url=recording_url,
    )


@router.post(
    "/{session_id}/materials",
    response_model=UploadMaterialsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload presentation materials",
)
async def upload_materials(
    session_id: UUID,
    current_user_id: CurrentUserDep,
    materials: UploadFile = File(
        ..., description="Presentation materials (PPT or PDF)"
    ),
):
    """Upload presentation materials (PPT/PDF) for a session.

    Associates the materials with the presentation session.
    Requirement 7.2: Associate materials with the session.
    """
    file_data = await materials.read()

    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Materials file is empty",
        )

    filename = materials.filename or "materials.pdf"
    service = _get_presentation_service()

    try:
        materials_url = await service.upload_materials(
            user_id=current_user_id,
            session_id=session_id,
            file_data=file_data,
            filename=filename,
        )
    except PresentationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Presentation session not found or access denied",
        )
    except PresentationServiceError as e:
        logger.error("Failed to upload materials: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload materials. Please try again.",
        )

    return UploadMaterialsResponse(
        session_id=session_id,
        materials_url=materials_url,
    )


@router.post(
    "/{session_id}/complete",
    response_model=CompletePresentationResponse,
    summary="Complete a presentation session and get analysis report",
)
async def complete_presentation_session(
    session_id: UUID,
    current_user_id: CurrentUserDep,
):
    """Complete a presentation session and generate the analysis report.

    Analyzes the presentation recording for speaking speed, clarity,
    structure, communication, and engagement. Returns scores and
    improvement suggestions.

    Requirements 7.3, 7.4, 7.5: Analyze and generate scores/feedback.
    """
    service = _get_presentation_service()

    try:
        result = await service.complete_session(
            user_id=current_user_id,
            session_id=session_id,
        )
    except PresentationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Presentation session not found or access denied",
        )
    except PresentationServiceError as e:
        logger.error("Failed to complete presentation session: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete presentation session. Please try again.",
        )

    # Build response
    session_data = result["session"]
    scores = result.get("scores")
    feedback = result.get("feedback")

    scores_response = None
    if scores:
        scores_response = PresentationScoresResponse(
            speaking_speed=scores.speaking_speed,
            clarity=scores.clarity,
            structure=scores.structure,
            communication=scores.communication,
            engagement=scores.engagement,
        )

    feedback_response = None
    if feedback:
        feedback_response = PresentationFeedbackResponse(
            strengths=feedback.strengths,
            weaknesses=feedback.weaknesses,
            recommendations=feedback.recommendations,
            presentation_scores=scores_response,
        )

    return CompletePresentationResponse(
        session=_session_to_response(session_data),
        scores=scores_response,
        feedback=feedback_response,
    )
