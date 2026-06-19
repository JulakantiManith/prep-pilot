"""Pydantic schemas for analytics endpoints."""

from pydantic import BaseModel, Field

from app.models.analytics import AnalyticsOverview, ScoreTrend


class RecentSession(BaseModel):
    """A single recent session entry for the dashboard."""

    session_type: str
    created_at: str
    overall_score: int | None = None


class AnalyticsOverviewResponse(BaseModel):
    """Response schema for the analytics overview endpoint.

    Includes aggregate metrics, weekly progress chart data,
    and recent sessions for the dashboard.
    """

    has_sessions: bool = Field(
        description="Whether the user has any completed sessions. "
        "If false, the frontend should show onboarding state."
    )
    overview: AnalyticsOverview = Field(
        description="Aggregate metrics for the dashboard cards."
    )
    weekly_progress: list[ScoreTrend] = Field(
        default_factory=list,
        description="Daily score averages for the current week (Monday-Sunday).",
    )
    recent_sessions: list[RecentSession] = Field(
        default_factory=list,
        description="The 5 most recent completed sessions.",
    )
