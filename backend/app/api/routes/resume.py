"""Resume parsing and management API routes.

Provides endpoints for parsing resumes, viewing/editing extracted data,
and confirming extracted data before question generation.

Requirements: 6.1, 6.2, 6.3, 6.4
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.schemas.resume_schemas import (
    ResumeConfirmResponse,
    ResumeEditRequest,
    ResumeExtractedResponse,
    ResumeParseResponse,
)
from app.dependencies import CurrentUserDep
from app.integrations.supabase_client import get_supabase_client
from app.services.resume_parser import ResumeParserError, get_resume_parser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post(
    "/parse",
    response_model=ResumeParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse an uploaded resume",
)
async def parse_resume(
    current_user_id: CurrentUserDep,
    resume_id: str,
):
    """Trigger extraction of structured data from an uploaded resume.

    The resume must already be uploaded via the profile resume upload endpoint.
    Extracts skills, projects, experience, and education sections.
    Extraction completes within 60 seconds and includes a confidence score.

    If extraction fails, returns an error message suggesting the user
    re-upload a properly formatted resume.
    """
    parser = get_resume_parser()

    try:
        result = await parser.parse_resume(
            resume_id=resume_id,
            user_id=current_user_id,
        )

        return ResumeParseResponse(
            id=resume_id,
            extraction_status="completed",
            extracted_data=result["extracted_data"],
            extraction_confidence=result["confidence"],
        )

    except ResumeParserError as e:
        logger.warning(
            "Resume parsing failed for user %s, resume %s: %s",
            current_user_id,
            resume_id,
            str(e),
        )
        return ResumeParseResponse(
            id=resume_id,
            extraction_status="failed",
            message=str(e),
        )


@router.get(
    "/extracted/{resume_id}",
    response_model=ResumeExtractedResponse,
    summary="Get extracted resume data",
)
async def get_extracted_data(
    current_user_id: CurrentUserDep,
    resume_id: str,
):
    """Get the extracted data for a specific resume.

    User must own the resume to access its data.
    Returns extracted fields (skills, projects, experience, education),
    confidence score, and confirmation status.
    """
    client = get_supabase_client()

    try:
        response = (
            client.table("resumes")
            .select("*")
            .eq("id", resume_id)
            .eq("user_id", current_user_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or access denied",
            )

        record = response.data[0]

        return ResumeExtractedResponse(
            id=record["id"],
            user_id=record["user_id"],
            file_name=record["file_name"],
            extracted_data=record.get("extracted_data"),
            extraction_confidence=record.get("extraction_confidence"),
            extraction_status=record["extraction_status"],
            user_confirmed=record.get("user_confirmed", False),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get extracted data for resume %s: %s", resume_id, str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve extracted resume data",
        ) from e


@router.put(
    "/extracted/{resume_id}",
    response_model=ResumeExtractedResponse,
    summary="Edit extracted resume data",
)
async def edit_extracted_data(
    current_user_id: CurrentUserDep,
    resume_id: str,
    request: ResumeEditRequest,
):
    """Manually edit extracted resume data.

    Allows the user to modify any extracted fields (skills, projects,
    experience, education) before confirming. Only provided fields
    are updated; omitted fields are left unchanged.

    User must own the resume to edit its data.
    """
    client = get_supabase_client()

    try:
        # Verify ownership
        existing = (
            client.table("resumes")
            .select("*")
            .eq("id", resume_id)
            .eq("user_id", current_user_id)
            .execute()
        )

        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or access denied",
            )

        record = existing.data[0]

        # Cannot edit after confirmation
        if record.get("user_confirmed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot edit resume data after confirmation",
            )

        # Merge updates into existing extracted data
        current_data = record.get("extracted_data") or {}
        update_fields = request.model_dump(exclude_unset=True)

        for field, value in update_fields.items():
            if value is not None:
                current_data[field] = value

        # Update in database
        response = (
            client.table("resumes")
            .update({"extracted_data": current_data})
            .eq("id", resume_id)
            .eq("user_id", current_user_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update extracted data",
            )

        updated = response.data[0]

        return ResumeExtractedResponse(
            id=updated["id"],
            user_id=updated["user_id"],
            file_name=updated["file_name"],
            extracted_data=updated.get("extracted_data"),
            extraction_confidence=updated.get("extraction_confidence"),
            extraction_status=updated["extraction_status"],
            user_confirmed=updated.get("user_confirmed", False),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to edit extracted data for resume %s: %s", resume_id, str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update extracted resume data",
        ) from e


@router.post(
    "/confirm/{resume_id}",
    response_model=ResumeConfirmResponse,
    summary="Confirm extracted resume data",
)
async def confirm_extracted_data(
    current_user_id: CurrentUserDep,
    resume_id: str,
):
    """Confirm the extracted resume data for question generation.

    Marks the resume data as confirmed by the user. Questions are
    ONLY generated after this confirmation step. Once confirmed,
    the extracted data cannot be edited.

    User must own the resume to confirm its data.
    """
    client = get_supabase_client()

    try:
        # Verify ownership and check status
        existing = (
            client.table("resumes")
            .select("*")
            .eq("id", resume_id)
            .eq("user_id", current_user_id)
            .execute()
        )

        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or access denied",
            )

        record = existing.data[0]

        # Check if already confirmed
        if record.get("user_confirmed"):
            return ResumeConfirmResponse(
                id=resume_id,
                user_confirmed=True,
                message="Resume data was already confirmed.",
            )

        # Verify extraction is completed
        if record.get("extraction_status") != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot confirm resume data before extraction is completed",
            )

        # Verify there is extracted data
        if not record.get("extracted_data"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No extracted data available to confirm",
            )

        # Mark as confirmed
        response = (
            client.table("resumes")
            .update({"user_confirmed": True})
            .eq("id", resume_id)
            .eq("user_id", current_user_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to confirm resume data",
            )

        return ResumeConfirmResponse(
            id=resume_id,
            user_confirmed=True,
            message="Resume data confirmed. You can now generate personalized interview questions.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to confirm resume data for resume %s: %s", resume_id, str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm resume data",
        ) from e
