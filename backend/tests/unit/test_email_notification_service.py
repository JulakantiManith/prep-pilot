"""Unit tests for the email notification service.

Tests cover template rendering with session data, non-blocking fire-and-forget
behavior, score color mapping, and edge cases.

Requirements: 1.1, 1.4, 1.5, 17.2
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.email_notification_service import (
    _build_plain_text,
    _get_score_color,
    _render_template,
    send_session_complete_notification,
)


@pytest.fixture
def session_summary():
    """Standard session summary data for testing."""
    return {
        "session_type": "HR Interview",
        "completed_at": "2024-06-15T14:30:00Z",
        "overall_score": 82.5,
        "strengths": ["Clear communication", "Good eye contact"],
        "weaknesses": ["Pacing could improve"],
        "session_id": "abc-123-def",
    }


@pytest.fixture
def mock_settings():
    """Mock settings returning a production frontend URL."""
    settings = MagicMock()
    settings.get_resolved_frontend_url.return_value = "https://app.interviewcoach.com"
    return settings


class TestScoreColorMapping:
    """Tests for _get_score_color function."""

    def test_high_score_returns_green(self) -> None:
        """Score >= 70 returns green."""
        assert _get_score_color(85.0) == "#16a34a"

    def test_moderate_score_returns_amber(self) -> None:
        """Score >= 50 and < 70 returns amber."""
        assert _get_score_color(55.0) == "#d97706"

    def test_low_score_returns_red(self) -> None:
        """Score < 50 returns red."""
        assert _get_score_color(30.0) == "#dc2626"

    def test_none_score_returns_gray(self) -> None:
        """None score returns gray."""
        assert _get_score_color(None) == "#6b7280"

    def test_boundary_at_70(self) -> None:
        """Exactly 70 returns green."""
        assert _get_score_color(70.0) == "#16a34a"

    def test_boundary_at_50(self) -> None:
        """Exactly 50 returns amber."""
        assert _get_score_color(50.0) == "#d97706"


class TestTemplateRendering:
    """Tests for template rendering with session data."""

    @patch("app.services.email_notification_service.get_settings")
    def test_renders_all_placeholders(self, mock_get_settings, session_summary) -> None:
        """Verify all template placeholders are replaced with session data."""
        settings = MagicMock()
        settings.get_resolved_frontend_url.return_value = "https://app.interviewcoach.com"
        mock_get_settings.return_value = settings

        html = _render_template(session_summary)

        # All placeholders should be replaced
        assert "{{ session_type }}" not in html
        assert "{{ session_date }}" not in html
        assert "{{ overall_score }}" not in html
        assert "{{ score_color }}" not in html
        assert "{{ strength_1 }}" not in html
        assert "{{ strength_2 }}" not in html
        assert "{{ improvement_area }}" not in html
        assert "{{ report_url }}" not in html

        # Actual values should be present
        assert "HR Interview" in html
        assert "June 15, 2024" in html
        assert "82" in html
        assert "#16a34a" in html  # green for score 82.5
        assert "Clear communication" in html
        assert "Good eye contact" in html
        assert "Pacing could improve" in html
        assert "https://app.interviewcoach.com/history/abc-123-def" in html

    @patch("app.services.email_notification_service.get_settings")
    def test_renders_with_missing_strengths(self, mock_get_settings) -> None:
        """Verify template renders safely when strengths list is empty."""
        settings = MagicMock()
        settings.get_resolved_frontend_url.return_value = "https://app.example.com"
        mock_get_settings.return_value = settings

        summary = {
            "session_type": "Technical Interview",
            "completed_at": "2024-01-01T00:00:00Z",
            "overall_score": 45.0,
            "strengths": [],
            "weaknesses": [],
            "session_id": "sess-001",
        }

        html = _render_template(summary)

        assert "Keep practicing!" in html
        assert "No specific areas flagged" in html

    @patch("app.services.email_notification_service.get_settings")
    def test_renders_with_none_score(self, mock_get_settings) -> None:
        """Verify template renders 'N/A' when overall_score is None."""
        settings = MagicMock()
        settings.get_resolved_frontend_url.return_value = "https://app.example.com"
        mock_get_settings.return_value = settings

        summary = {
            "session_type": "Behavioral",
            "completed_at": "",
            "overall_score": None,
            "strengths": ["One strength"],
            "weaknesses": ["One weakness"],
            "session_id": "sess-002",
        }

        html = _render_template(summary)

        assert "N/A" in html
        assert "#6b7280" in html  # gray for None score

    @patch("app.services.email_notification_service.get_settings")
    def test_report_url_uses_frontend_url(self, mock_get_settings, session_summary) -> None:
        """Verify report URL is constructed from resolved frontend URL."""
        settings = MagicMock()
        settings.get_resolved_frontend_url.return_value = "https://custom.domain.com"
        mock_get_settings.return_value = settings

        html = _render_template(session_summary)

        assert "https://custom.domain.com/history/abc-123-def" in html

    @patch("app.services.email_notification_service.get_settings")
    def test_renders_with_empty_completed_at(self, mock_get_settings) -> None:
        """Verify template shows 'Today' when completed_at is empty."""
        settings = MagicMock()
        settings.get_resolved_frontend_url.return_value = "https://app.example.com"
        mock_get_settings.return_value = settings

        summary = {
            "session_type": "HR Interview",
            "completed_at": "",
            "overall_score": 75.0,
            "strengths": ["Good answer"],
            "weaknesses": ["Slow pace"],
            "session_id": "sess-003",
        }

        html = _render_template(summary)

        assert "Today" in html


class TestNonBlockingBehavior:
    """Tests for fire-and-forget email sending."""

    @pytest.mark.asyncio
    async def test_does_not_raise_on_email_client_error(
        self, session_summary
    ) -> None:
        """Verify notification swallows exceptions (fire-and-forget)."""
        with patch(
            "app.services.email_notification_service.email_client"
        ) as mock_client:
            mock_client.send_email = AsyncMock(
                side_effect=Exception("SMTP connection failed")
            )

            # Should not raise
            await send_session_complete_notification(
                "user@example.com", session_summary
            )

    @pytest.mark.asyncio
    async def test_does_not_raise_on_template_error(self) -> None:
        """Verify notification swallows template rendering errors."""
        with patch(
            "app.services.email_notification_service._load_template",
            side_effect=FileNotFoundError("Template missing"),
        ):
            # Should not raise
            await send_session_complete_notification(
                "user@example.com", {"session_type": "Test"}
            )

    @pytest.mark.asyncio
    async def test_calls_email_client_with_correct_args(
        self, session_summary
    ) -> None:
        """Verify notification service passes correct data to email client."""
        with patch(
            "app.services.email_notification_service.email_client"
        ) as mock_client:
            mock_client.send_email = AsyncMock(return_value=True)

            with patch("app.services.email_notification_service.get_settings") as mock_get:
                settings = MagicMock()
                settings.get_resolved_frontend_url.return_value = "https://app.example.com"
                mock_get.return_value = settings

                await send_session_complete_notification(
                    "user@test.com", session_summary
                )

        mock_client.send_email.assert_called_once()
        call_kwargs = mock_client.send_email.call_args[1]
        assert call_kwargs["to"] == "user@test.com"
        assert "HR Interview" in call_kwargs["subject"]
        assert "<" in call_kwargs["html_body"]  # Contains HTML
        assert call_kwargs["text_body"] is not None


class TestPlainTextBuilder:
    """Tests for plain-text email fallback construction."""

    @patch("app.services.email_notification_service.get_settings")
    def test_plain_text_includes_session_data(
        self, mock_get_settings, session_summary
    ) -> None:
        """Verify plain text contains score, strengths, and report URL."""
        settings = MagicMock()
        settings.get_resolved_frontend_url.return_value = "https://app.example.com"
        mock_get_settings.return_value = settings

        text = _build_plain_text(session_summary)

        assert "HR Interview" in text
        assert "82/100" in text
        assert "Clear communication" in text
        assert "Pacing could improve" in text
        assert "https://app.example.com/history/abc-123-def" in text

    @patch("app.services.email_notification_service.get_settings")
    def test_plain_text_handles_none_score(self, mock_get_settings) -> None:
        """Verify plain text shows N/A for None score."""
        settings = MagicMock()
        settings.get_resolved_frontend_url.return_value = "https://app.example.com"
        mock_get_settings.return_value = settings

        summary = {
            "session_type": "Presentation",
            "overall_score": None,
            "strengths": [],
            "weaknesses": [],
            "session_id": "sess-x",
        }

        text = _build_plain_text(summary)

        assert "N/A" in text
        assert "Keep practicing!" in text
