"""Analytics API routes."""

import logging
from enum import Enum

from fastapi import APIRouter, HTTPException, Query, status

from app.api.schemas.analytics_schemas import AnalyticsOverviewResponse, RecentSession
from app.dependencies import CurrentUserDep
from app.repositories.session_repository import RepositoryError
from app.services.analytics_service import get_analytics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


class TimeRange(str, Enum):
    """Supported time range options for progress chart."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    THREE_MONTHS = "3months"
    YEARLY = "yearly"


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get dashboard analytics overview",
)
async def get_analytics_overview(
    current_user_id: CurrentUserDep,
    time_range: TimeRange = Query(
        default=TimeRange.WEEKLY,
        description="Time range for the progress chart: daily, weekly, monthly, 3months, yearly",
    ),
):
    """Get the authenticated user's dashboard analytics overview.

    Returns aggregate metrics (total sessions, average score,
    confidence/communication scores), progress chart data for the
    selected time range, and the 5 most recent sessions.

    If the user has no completed sessions, has_sessions will be false
    and the frontend should display an onboarding state.
    """
    try:
        analytics_service = get_analytics_service()
        result = analytics_service.get_overview(
            user_id=current_user_id, time_range=time_range.value
        )

        # Map recent sessions to response schema
        recent_sessions = [
            RecentSession(
                session_type=s.get("session_type", ""),
                created_at=s.get("created_at", ""),
                overall_score=s.get("overall_score"),
            )
            for s in result["recent_sessions"]
        ]

        return AnalyticsOverviewResponse(
            has_sessions=result["has_sessions"],
            overview=result["overview"],
            weekly_progress=result["weekly_progress"],
            recent_sessions=recent_sessions,
        )
    except RepositoryError as e:
        logger.error(
            "Repository error fetching analytics for user %s: %s",
            current_user_id,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics data",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error fetching analytics for user %s: %s",
            current_user_id,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics data",
        ) from e
