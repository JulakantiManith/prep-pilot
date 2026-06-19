"""Analytics service for computing dashboard metrics.

Provides business logic for aggregating session data into
dashboard-ready analytics including overview metrics, weekly
progress chart data, and recent sessions.

Requirements: 3.1, 3.2, 3.3, 3.4
"""

import logging
from datetime import UTC, datetime, timedelta

from app.models.analytics import AnalyticsOverview, ScoreTrend
from app.repositories.analytics_repository import AnalyticsRepository

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service layer for analytics and dashboard data."""

    def __init__(self) -> None:
        """Initialize with analytics repository."""
        self._repository = AnalyticsRepository()

    def get_overview(self, user_id: str, time_range: str = "weekly") -> dict:
        """Get the complete dashboard overview for a user.

        Computes aggregate metrics, progress chart data for the selected
        time range, and recent sessions list.

        Args:
            user_id: The authenticated user's ID.
            time_range: One of 'daily', 'weekly', 'monthly', '3months', 'yearly'.

        Returns:
            Dictionary containing:
              - has_sessions: bool indicating if user has any completed sessions
              - overview: AnalyticsOverview metrics
              - weekly_progress: list of ScoreTrend for selected time range
              - recent_sessions: list of recent session summaries
        """
        # Get session counts by type
        total_interview = self._repository.get_completed_sessions_count_by_type(
            user_id, "interview"
        )
        total_presentation = self._repository.get_completed_sessions_count_by_type(
            user_id, "presentation"
        )

        total_sessions = total_interview + total_presentation
        has_sessions = total_sessions > 0

        # Get average overall score
        average_score = self._repository.get_average_overall_score(user_id)

        # Get latest confidence and communication scores
        latest_scores = self._repository.get_latest_session_scores(user_id)
        latest_confidence = None
        latest_communication = None
        if latest_scores:
            latest_confidence = latest_scores.get("confidence_score")
            latest_communication = latest_scores.get("communication_score")

        overview = AnalyticsOverview(
            total_interview_sessions=total_interview,
            total_presentation_sessions=total_presentation,
            average_overall_score=average_score,
            latest_confidence_score=latest_confidence,
            latest_communication_score=latest_communication,
        )

        # Get weekly progress chart data
        weekly_progress = self._get_progress(user_id, time_range)

        # Get recent sessions
        recent_sessions = self._repository.get_recent_sessions(user_id, limit=5)

        return {
            "has_sessions": has_sessions,
            "overview": overview,
            "weekly_progress": weekly_progress,
            "recent_sessions": recent_sessions,
        }

    def _get_progress(self, user_id: str, time_range: str) -> list[ScoreTrend]:
        """Get score aggregates for the selected time range.

        Args:
            user_id: The authenticated user's ID.
            time_range: One of 'daily', 'weekly', 'monthly', '3months', 'yearly'.

        Returns:
            List of ScoreTrend objects for the selected period.
        """
        today = datetime.now(UTC).date()

        if time_range == "daily":
            # Today only
            start = today
            end = today
        elif time_range == "weekly":
            # Current week (Monday-Sunday)
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
        elif time_range == "monthly":
            # Last 30 days
            start = today - timedelta(days=29)
            end = today
        elif time_range == "3months":
            # Last 90 days
            start = today - timedelta(days=89)
            end = today
        elif time_range == "yearly":
            # Last 365 days
            start = today - timedelta(days=364)
            end = today
        else:
            # Default to weekly
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)

        start_date = f"{start}T00:00:00"
        end_date = f"{end}T23:59:59"

        sessions = self._repository.get_sessions_for_date_range(
            user_id, start_date, end_date
        )

        if not sessions:
            return []

        # Group sessions by date and compute daily averages
        daily_data: dict[str, list[int]] = {}
        for session in sessions:
            completed_at = session.get("completed_at", "")
            score = session.get("overall_score")
            if not completed_at or score is None:
                continue

            # Extract date portion (YYYY-MM-DD)
            date_str = completed_at[:10]
            if date_str not in daily_data:
                daily_data[date_str] = []
            daily_data[date_str].append(score)

        # Build ScoreTrend list sorted by date
        trends = []
        for date_str in sorted(daily_data.keys()):
            scores = daily_data[date_str]
            avg_score = round(sum(scores) / len(scores), 1)
            trends.append(
                ScoreTrend(
                    date=date_str,
                    average_score=avg_score,
                    session_count=len(scores),
                )
            )

        return trends


def get_analytics_service() -> AnalyticsService:
    """Factory function for AnalyticsService dependency injection."""
    return AnalyticsService()
