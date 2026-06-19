"""Unit tests for the analytics service."""

from unittest.mock import MagicMock, patch

import pytest

from app.models.analytics import AnalyticsOverview, ScoreTrend
from app.services.analytics_service import AnalyticsService


@pytest.fixture
def mock_repository():
    """Create a mock analytics repository."""
    with patch(
        "app.services.analytics_service.AnalyticsRepository"
    ) as MockRepo:
        mock_repo = MagicMock()
        MockRepo.return_value = mock_repo
        yield mock_repo


@pytest.fixture
def service(mock_repository):
    """Create an AnalyticsService with mocked repository."""
    return AnalyticsService()


class TestGetOverview:
    """Tests for AnalyticsService.get_overview."""

    def test_returns_has_sessions_false_when_no_sessions(
        self, service, mock_repository
    ):
        """When user has zero completed sessions, has_sessions is False."""
        mock_repository.get_completed_sessions_count_by_type.return_value = 0
        mock_repository.get_average_overall_score.return_value = None
        mock_repository.get_latest_session_scores.return_value = None
        mock_repository.get_sessions_for_date_range.return_value = []
        mock_repository.get_recent_sessions.return_value = []

        result = service.get_overview("user-123")

        assert result["has_sessions"] is False
        assert result["overview"].total_interview_sessions == 0
        assert result["overview"].total_presentation_sessions == 0
        assert result["overview"].average_overall_score is None
        assert result["weekly_progress"] == []
        assert result["recent_sessions"] == []

    def test_returns_has_sessions_true_with_sessions(
        self, service, mock_repository
    ):
        """When user has completed sessions, has_sessions is True."""
        mock_repository.get_completed_sessions_count_by_type.side_effect = [
            3,  # interview
            2,  # presentation
        ]
        mock_repository.get_average_overall_score.return_value = 75.5
        mock_repository.get_latest_session_scores.return_value = {
            "confidence_score": 80,
            "communication_score": 70,
        }
        mock_repository.get_sessions_for_date_range.return_value = []
        mock_repository.get_recent_sessions.return_value = [
            {
                "session_type": "interview",
                "created_at": "2024-01-15T10:00:00",
                "overall_score": 85,
            }
        ]

        result = service.get_overview("user-123")

        assert result["has_sessions"] is True
        assert result["overview"].total_interview_sessions == 3
        assert result["overview"].total_presentation_sessions == 2
        assert result["overview"].average_overall_score == 75.5
        assert result["overview"].latest_confidence_score == 80
        assert result["overview"].latest_communication_score == 70
        assert len(result["recent_sessions"]) == 1

    def test_weekly_progress_aggregates_by_day(
        self, service, mock_repository
    ):
        """Weekly progress groups sessions by date and computes averages."""
        mock_repository.get_completed_sessions_count_by_type.return_value = 0
        mock_repository.get_average_overall_score.return_value = None
        mock_repository.get_latest_session_scores.return_value = None
        mock_repository.get_sessions_for_date_range.return_value = [
            {"completed_at": "2024-01-15T10:00:00", "overall_score": 80},
            {"completed_at": "2024-01-15T14:00:00", "overall_score": 90},
            {"completed_at": "2024-01-16T09:00:00", "overall_score": 70},
        ]
        mock_repository.get_recent_sessions.return_value = []

        result = service.get_overview("user-123")

        weekly = result["weekly_progress"]
        assert len(weekly) == 2
        # First day: average of 80 and 90
        assert weekly[0].date == "2024-01-15"
        assert weekly[0].average_score == 85.0
        assert weekly[0].session_count == 2
        # Second day: only 70
        assert weekly[1].date == "2024-01-16"
        assert weekly[1].average_score == 70.0
        assert weekly[1].session_count == 1

    def test_latest_scores_none_when_no_sessions(
        self, service, mock_repository
    ):
        """When no sessions exist, latest scores are None."""
        mock_repository.get_completed_sessions_count_by_type.return_value = 0
        mock_repository.get_average_overall_score.return_value = None
        mock_repository.get_latest_session_scores.return_value = None
        mock_repository.get_sessions_for_date_range.return_value = []
        mock_repository.get_recent_sessions.return_value = []

        result = service.get_overview("user-123")

        assert result["overview"].latest_confidence_score is None
        assert result["overview"].latest_communication_score is None

    def test_recent_sessions_returns_up_to_five(
        self, service, mock_repository
    ):
        """Recent sessions calls repository with limit=5."""
        mock_repository.get_completed_sessions_count_by_type.return_value = 0
        mock_repository.get_average_overall_score.return_value = None
        mock_repository.get_latest_session_scores.return_value = None
        mock_repository.get_sessions_for_date_range.return_value = []
        mock_repository.get_recent_sessions.return_value = []

        service.get_overview("user-123")

        mock_repository.get_recent_sessions.assert_called_once_with(
            "user-123", limit=5
        )
