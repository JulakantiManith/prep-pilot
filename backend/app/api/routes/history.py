"""Session history API routes.

Provides paginated, filterable access to past session data
and full detail views for individual sessions.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import logging
import math
from typing import Optional
from uuid import UUID as UUIDType

from fastapi import APIRouter, HTTPException, Query, status

from app.api.schemas.history_schemas import (
    AnswerDetail,
    SessionDetailResponse,
    SessionFeedbackDetail,
    SessionHistoryListResponse,
    SessionListItem,
)
from app.dependencies import CurrentUserDep
from app.integrations.supabase_client import get_supabase_client
from app.repositories.session_repository import RepositoryError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["History"])

PAGE_SIZE = 20


@router.get(
    "",
    response_model=SessionHistoryListResponse,
    summary="Get paginated session history",
)
async def get_session_history(
    current_user_id: CurrentUserDep,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    session_type: Optional[str] = Query(
        default=None,
        description="Filter by session type: 'interview' or 'presentation'",
    ),
    start_date: Optional[str] = Query(
        default=None,
        description="Filter sessions from this date (ISO format, e.g. 2024-01-01)",
    ),
    end_date: Optional[str] = Query(
        default=None,
        description="Filter sessions up to this date (ISO format, e.g. 2024-12-31)",
    ),
):
    """Get a paginated list of all past sessions sorted by date (most recent first).

    Supports filtering by session_type and date range.
    Returns 20 sessions per page with total count and total pages.

    Requirements: 12.1, 12.2, 12.4, 12.5
    """
    try:
        client = get_supabase_client()

        # Build base query for counting
        # Include completed, processing, and failed sessions
        # Note: 'processing' requires the session_status enum to include it
        # (run supabase_add_processing_status.sql if not already done)
        valid_statuses = ["completed", "processing", "failed"]
        count_query = (
            client.table("sessions")
            .select("id", count="exact")
            .eq("user_id", current_user_id)
            .in_("status", valid_statuses)
        )

        # Build base query for data
        data_query = (
            client.table("sessions")
            .select(
                "id, session_type, created_at, duration_seconds, overall_score, status"
            )
            .eq("user_id", current_user_id)
            .in_("status", valid_statuses)
        )

        # Apply optional filters
        if session_type:
            count_query = count_query.eq("session_type", session_type)
            data_query = data_query.eq("session_type", session_type)

        if start_date:
            count_query = count_query.gte("created_at", start_date)
            data_query = data_query.gte("created_at", start_date)

        if end_date:
            # Include the full end date day by appending time
            end_date_full = f"{end_date}T23:59:59.999999"
            count_query = count_query.lte("created_at", end_date_full)
            data_query = data_query.lte("created_at", end_date_full)

        # Execute count query
        count_response = count_query.execute()
        total_count = count_response.count if count_response.count is not None else 0

        # Calculate pagination
        total_pages = math.ceil(total_count / PAGE_SIZE) if total_count > 0 else 0
        offset = (page - 1) * PAGE_SIZE

        # Execute data query with pagination and sorting
        data_response = (
            data_query.order("created_at", desc=True)
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )

        sessions = [
            SessionListItem(
                id=s["id"],
                session_type=s.get("session_type", ""),
                created_at=s.get("created_at", ""),
                duration_seconds=s.get("duration_seconds"),
                overall_score=s.get("overall_score"),
                status=s.get("status", "completed"),
            )
            for s in (data_response.data or [])
        ]

        return SessionHistoryListResponse(
            sessions=sessions,
            total_count=total_count,
            total_pages=total_pages,
            page=page,
            page_size=PAGE_SIZE,
        )

    except RepositoryError as e:
        logger.error(
            "Repository error fetching history for user %s: %s",
            current_user_id,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session history",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error fetching history for user %s: %s",
            current_user_id,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session history",
        ) from e


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    summary="Get full session detail",
)
async def get_session_detail(
    session_id: str,
    current_user_id: CurrentUserDep,
):
    """Get the full detail of a specific session including transcript, scores, and feedback.

    Returns 404 if the session is not found or doesn't belong to the authenticated user.

    Requirement: 12.3
    """
    try:
        client = get_supabase_client()

        # Fetch session data filtered by user_id for data isolation
        session_response = (
            client.table("sessions")
            .select("*")
            .eq("id", session_id)
            .eq("user_id", current_user_id)
            .execute()
        )

        if not session_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        session = session_response.data[0]

        # Fetch all answers for this session ordered by question_index
        answers_response = (
            client.table("answers")
            .select("*")
            .eq("session_id", session_id)
            .order("question_index")
            .execute()
        )

        answers = [
            AnswerDetail(
                question_index=a.get("question_index", 0),
                question_text=a.get("question_text"),
                transcript=a.get("transcript"),
                wpm=a.get("wpm"),
                total_words=a.get("total_words"),
                filler_word_count=a.get("filler_word_count"),
                filler_words_detail=a.get("filler_words_detail"),
                speaking_duration=a.get("speaking_duration"),
                avg_pause_duration=a.get("avg_pause_duration"),
                communication_score=a.get("communication_score"),
                confidence_score=a.get("confidence_score"),
                ai_evaluation=a.get("ai_evaluation"),
                created_at=a.get("created_at"),
            )
            for a in (answers_response.data or [])
        ]

        # Fetch session feedback
        feedback_response = (
            client.table("session_feedback")
            .select("*")
            .eq("session_id", session_id)
            .execute()
        )

        feedback = None
        if feedback_response.data:
            fb = feedback_response.data[0]
            feedback = SessionFeedbackDetail(
                strengths=fb.get("strengths"),
                weaknesses=fb.get("weaknesses"),
                recommendations=fb.get("recommendations"),
                technical_evaluation=fb.get("technical_evaluation"),
                presentation_scores=fb.get("presentation_scores"),
            )
        elif session.get("status") == "completed" and (answers_response.data or []):
            # No feedback persisted for this completed session — generate algorithmic feedback
            # without calling Gemini API to conserve API quota
            try:
                from app.services.ai_feedback_service import (
                    AIFeedbackService,
                    AnswerData,
                    SessionData,
                )
                from app.services.speech_analysis_service import SpeechAnalysisService
                from app.models.session import InterviewType

                raw_answers = answers_response.data or []
                transcripts = [
                    a.get("transcript", "") for a in raw_answers if a.get("transcript")
                ]
                combined_transcript = " ".join(transcripts)

                if combined_transcript.strip():
                    # Compute speech metrics for algorithmic feedback
                    speech_service = SpeechAnalysisService()
                    total_duration = sum(
                        a.get("speaking_duration", 0) or 0 for a in raw_answers
                    )
                    if total_duration <= 0:
                        word_count = len(combined_transcript.split())
                        total_duration = max(word_count / 2.5, 1.0)

                    speech_metrics = speech_service.analyze(
                        combined_transcript, total_duration
                    )

                    # Get average confidence score
                    confidence_scores = [
                        a["confidence_score"]
                        for a in raw_answers
                        if a.get("confidence_score") is not None
                    ]
                    avg_confidence = (
                        int(sum(confidence_scores) / len(confidence_scores))
                        if confidence_scores
                        else 50
                    )

                    # Build session data for algorithmic feedback
                    interview_type_str = session.get("interview_type", "hr")
                    try:
                        interview_type = InterviewType(interview_type_str)
                    except ValueError:
                        interview_type = InterviewType.HR

                    answer_data_list = [
                        AnswerData(
                            question_text=a.get("question_text", ""),
                            transcript=a.get("transcript", ""),
                            communication_score=a.get("communication_score"),
                            confidence_score=a.get("confidence_score"),
                        )
                        for a in raw_answers
                    ]

                    session_data = SessionData(
                        interview_type=interview_type,
                        role=session.get("role", ""),
                        topic=session.get("topic"),
                        difficulty=session.get("difficulty"),
                        answers=answer_data_list,
                    )

                    # Use algorithmic feedback only (no Gemini)
                    feedback_service = AIFeedbackService()
                    feedback_report = feedback_service._generate_algorithmic_feedback(
                        session_data=session_data,
                        speech_metrics=speech_metrics,
                        confidence_score=avg_confidence,
                    )
                    feedback_data = {
                        "strengths": feedback_report.strengths,
                        "weaknesses": feedback_report.weaknesses,
                        "recommendations": feedback_report.recommendations,
                        "technical_evaluation": feedback_report.technical_evaluation,
                        "presentation_scores": feedback_report.presentation_scores,
                    }
                else:
                    feedback_data = {
                        "strengths": [
                            "Completed all questions in the session",
                            "Showed commitment by finishing the interview",
                        ],
                        "weaknesses": [
                            "Responses were too brief to analyze in detail",
                            "Consider providing more detailed answers",
                        ],
                        "recommendations": [
                            "Practice giving more detailed verbal responses",
                            "Try to speak for at least 30-60 seconds per question",
                            "Structure your answers with clear beginning, middle, and end",
                        ],
                    }

                # Persist for future requests
                from app.repositories.session_repository import SessionRepository

                repo = SessionRepository()
                repo.create_session_feedback(UUIDType(session_id), feedback_data)
                feedback = SessionFeedbackDetail(
                    strengths=feedback_data.get("strengths"),
                    weaknesses=feedback_data.get("weaknesses"),
                    recommendations=feedback_data.get("recommendations"),
                    technical_evaluation=feedback_data.get("technical_evaluation"),
                    presentation_scores=feedback_data.get("presentation_scores"),
                )
                logger.info(
                    "Generated algorithmic feedback for legacy session %s",
                    session_id,
                )
            except Exception as e:
                logger.warning(
                    "Failed to generate feedback for legacy session %s: %s",
                    session_id,
                    str(e),
                )

        return SessionDetailResponse(
            id=session["id"],
            session_type=session.get("session_type", ""),
            interview_type=session.get("interview_type"),
            role=session.get("role"),
            topic=session.get("topic"),
            difficulty=session.get("difficulty"),
            overall_score=session.get("overall_score"),
            confidence_score=session.get("confidence_score"),
            communication_score=session.get("communication_score"),
            duration_seconds=session.get("duration_seconds"),
            status=session.get("status"),
            created_at=session.get("created_at", ""),
            completed_at=session.get("completed_at"),
            answers=answers,
            feedback=feedback,
        )

    except HTTPException:
        raise
    except RepositoryError as e:
        logger.error(
            "Repository error fetching session detail %s for user %s: %s",
            session_id,
            current_user_id,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session detail",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error fetching session detail %s for user %s: %s",
            session_id,
            current_user_id,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session detail",
        ) from e
