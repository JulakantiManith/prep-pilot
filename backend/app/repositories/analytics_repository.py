"""Analytics repository for database operations.

Provides data access methods for dashboard analytics using Supabase.
All queries filter by user_id for data isolation.

Requirements: 3.1, 3.2, 3.3
"""

import logging
from typing import Optional

from app.integrations.supabase_client import get_supabase_client
from app.repositories.session_repository import RepositoryError

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    """Repository for analytics database operations.

    All queries filter by user_id for data isolation.
    Read operations do not retry (standard fail-fast behavior).
    """

    def __init__(self) -> None:
        """Initialize with Supabase client."""
        self._client = get_supabase_client()

    def get_completed_sessions_count_by_type(
        self, user_id: str, session_type: str
    ) -> int:
        """Get count of completed sessions filtered by type.

        Args:
            user_id: The owning user's ID.
            session_type: Either 'interview' or 'presentation'.

        Returns:
            Count of completed sessions of the given type.
        """
        try:
            response = (
                self._client.table("sessions")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("session_type", session_type)
                .eq("status", "completed")
                .execute()
            )
            return response.count or 0
        except Exception as e:
            logger.error(
                "Failed to get session count for user %s, type %s: %s",
                user_id,
                session_type,
                str(e),
            )
            raise RepositoryError(
                f"Failed to get session count: {e}"
            ) from e

    def get_average_overall_score(self, user_id: str) -> Optional[float]:
        """Get the average overall score across all completed sessions.

        Args:
            user_id: The owning user's ID.

        Returns:
            Average overall score or None if no sessions have scores.
        """
        try:
            response = (
                self._client.table("sessions")
                .select("overall_score")
                .eq("user_id", user_id)
                .eq("status", "completed")
                .not_.is_("overall_score", "null")
                .execute()
            )
            if not response.data:
                return None

            scores = [row["overall_score"] for row in response.data]
            if not scores:
                return None

            return round(sum(scores) / len(scores), 1)
        except Exception as e:
            logger.error(
                "Failed to get average score for user %s: %s", user_id, str(e)
            )
            raise RepositoryError(
                f"Failed to get average score: {e}"
            ) from e

    def get_latest_session_scores(
        self, user_id: str
    ) -> Optional[dict]:
        """Get confidence and communication scores from the latest completed session.

        Args:
            user_id: The owning user's ID.

        Returns:
            Dict with confidence_score and communication_score, or None.
        """
        try:
            response = (
                self._client.table("sessions")
                .select("confidence_score, communication_score")
                .eq("user_id", user_id)
                .eq("status", "completed")
                .order("completed_at", desc=True)
                .limit(1)
                .execute()
            )
            if not response.data:
                return None

            return response.data[0]
        except Exception as e:
            logger.error(
                "Failed to get latest scores for user %s: %s", user_id, str(e)
            )
            raise RepositoryError(
                f"Failed to get latest scores: {e}"
            ) from e

    def get_sessions_for_date_range(
        self, user_id: str, start_date: str, end_date: str
    ) -> list[dict]:
        """Get completed sessions within a date range for weekly chart.

        Args:
            user_id: The owning user's ID.
            start_date: ISO format start date (inclusive).
            end_date: ISO format end date (inclusive).

        Returns:
            List of session dicts with overall_score and completed_at.
        """
        try:
            response = (
                self._client.table("sessions")
                .select("overall_score, completed_at")
                .eq("user_id", user_id)
                .eq("status", "completed")
                .not_.is_("overall_score", "null")
                .gte("completed_at", start_date)
                .lte("completed_at", end_date)
                .order("completed_at")
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(
                "Failed to get sessions for date range for user %s: %s",
                user_id,
                str(e),
            )
            raise RepositoryError(
                f"Failed to get sessions for date range: {e}"
            ) from e

    def get_recent_sessions(self, user_id: str, limit: int = 5) -> list[dict]:
        """Get the most recent completed sessions.

        Args:
            user_id: The owning user's ID.
            limit: Maximum number of sessions to return.

        Returns:
            List of session dicts with session_type, created_at, overall_score.
        """
        try:
            response = (
                self._client.table("sessions")
                .select("session_type, created_at, overall_score")
                .eq("user_id", user_id)
                .eq("status", "completed")
                .order("completed_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(
                "Failed to get recent sessions for user %s: %s", user_id, str(e)
            )
            raise RepositoryError(
                f"Failed to get recent sessions: {e}"
            ) from e
