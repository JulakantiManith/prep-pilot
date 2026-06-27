"""Integration tests for the async SMTP email client.

Tests cover SMTP connection behavior, email sending, retry logic on failure,
and graceful handling of connection errors.

Requirements: 1.1, 1.4, 17.2
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.email_client import (
    BASE_BACKOFF_SECONDS,
    EmailClient,
    EmailClientError,
    MAX_RETRIES,
)


@pytest.fixture
def smtp_settings():
    """Mock settings for SMTP configuration."""
    settings = MagicMock()
    settings.smtp_host = "smtp.example.com"
    settings.smtp_port = 587
    settings.smtp_username = "user@example.com"
    settings.smtp_password = "secret"
    settings.smtp_sender_email = "noreply@example.com"
    settings.smtp_sender_name = "AI Coach"
    settings.get_smtp_enabled.return_value = True
    return settings


@pytest.fixture
def disabled_smtp_settings():
    """Mock settings with SMTP disabled."""
    settings = MagicMock()
    settings.smtp_host = ""
    settings.smtp_port = 0
    settings.smtp_username = ""
    settings.smtp_password = ""
    settings.smtp_sender_email = ""
    settings.smtp_sender_name = ""
    settings.get_smtp_enabled.return_value = False
    return settings


@pytest.fixture
def email_client(smtp_settings):
    """Create an EmailClient with mocked settings."""
    with patch("app.integrations.email_client.get_settings", return_value=smtp_settings):
        client = EmailClient()
    return client


@pytest.fixture
def disabled_email_client(disabled_smtp_settings):
    """Create an EmailClient with SMTP disabled."""
    with patch(
        "app.integrations.email_client.get_settings",
        return_value=disabled_smtp_settings,
    ):
        client = EmailClient()
    return client


class TestEmailClientConnection:
    """Tests for SMTP connection and send behavior."""

    @pytest.mark.asyncio
    async def test_send_email_success(self, email_client: EmailClient) -> None:
        """Verify email is sent successfully when SMTP connection works."""
        mock_smtp = AsyncMock()
        mock_smtp.connect = AsyncMock()
        mock_smtp.starttls = AsyncMock()
        mock_smtp.login = AsyncMock()
        mock_smtp.send_message = AsyncMock()
        mock_smtp.quit = AsyncMock()

        with patch("app.integrations.email_client.aiosmtplib.SMTP", return_value=mock_smtp):
            result = await email_client.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                html_body="<h1>Hello</h1>",
            )

        assert result is True
        mock_smtp.connect.assert_called_once()
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user@example.com", "secret")
        mock_smtp.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_with_text_body(self, email_client: EmailClient) -> None:
        """Verify email includes plain-text fallback when provided."""
        mock_smtp = AsyncMock()
        mock_smtp.connect = AsyncMock()
        mock_smtp.starttls = AsyncMock()
        mock_smtp.login = AsyncMock()
        mock_smtp.send_message = AsyncMock()
        mock_smtp.quit = AsyncMock()

        with patch("app.integrations.email_client.aiosmtplib.SMTP", return_value=mock_smtp):
            result = await email_client.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                html_body="<h1>Hello</h1>",
                text_body="Hello in plain text",
            )

        assert result is True
        # Verify the message was sent (contains both parts)
        sent_message = mock_smtp.send_message.call_args[0][0]
        payloads = sent_message.get_payload()
        assert len(payloads) == 2  # plain text + HTML

    @pytest.mark.asyncio
    async def test_smtp_connection_uses_port_465_tls(self, smtp_settings) -> None:
        """Verify port 465 uses implicit TLS (no STARTTLS)."""
        smtp_settings.smtp_port = 465
        with patch("app.integrations.email_client.get_settings", return_value=smtp_settings):
            client = EmailClient()

        mock_smtp = AsyncMock()
        mock_smtp.connect = AsyncMock()
        mock_smtp.starttls = AsyncMock()
        mock_smtp.login = AsyncMock()
        mock_smtp.send_message = AsyncMock()
        mock_smtp.quit = AsyncMock()

        with patch("app.integrations.email_client.aiosmtplib.SMTP", return_value=mock_smtp) as mock_cls:
            await client.send_email(
                to="recipient@example.com",
                subject="Test",
                html_body="<p>Hi</p>",
            )

        # Port 465 = use_tls=True, no starttls call
        mock_cls.assert_called_once_with(
            hostname="smtp.example.com",
            port=465,
            use_tls=True,
            timeout=30.0,
        )
        mock_smtp.starttls.assert_not_called()


class TestEmailClientRetryLogic:
    """Tests for retry behavior on transient failures."""

    @pytest.mark.asyncio
    async def test_retries_on_smtp_exception(self, email_client: EmailClient) -> None:
        """Verify client retries once on SMTP failure then succeeds."""
        import aiosmtplib

        mock_smtp = AsyncMock()
        mock_smtp.connect = AsyncMock()
        mock_smtp.starttls = AsyncMock()
        mock_smtp.login = AsyncMock()
        mock_smtp.quit = AsyncMock()
        # Fail first, succeed second
        mock_smtp.send_message = AsyncMock(
            side_effect=[aiosmtplib.SMTPException("Temporary failure"), None]
        )

        with patch("app.integrations.email_client.aiosmtplib.SMTP", return_value=mock_smtp):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await email_client.send_email(
                    to="recipient@example.com",
                    subject="Retry Test",
                    html_body="<p>Retry</p>",
                )

        assert result is True
        assert mock_smtp.send_message.call_count == 2
        mock_sleep.assert_called_once_with(BASE_BACKOFF_SECONDS)

    @pytest.mark.asyncio
    async def test_raises_after_max_retries_exhausted(
        self, email_client: EmailClient
    ) -> None:
        """Verify EmailClientError raised after all retries are exhausted."""
        import aiosmtplib

        mock_smtp = AsyncMock()
        mock_smtp.connect = AsyncMock()
        mock_smtp.starttls = AsyncMock()
        mock_smtp.login = AsyncMock()
        mock_smtp.quit = AsyncMock()
        mock_smtp.send_message = AsyncMock(
            side_effect=aiosmtplib.SMTPException("Persistent failure")
        )

        with patch("app.integrations.email_client.aiosmtplib.SMTP", return_value=mock_smtp):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(EmailClientError) as exc_info:
                    await email_client.send_email(
                        to="recipient@example.com",
                        subject="Fail Test",
                        html_body="<p>Fail</p>",
                    )

        assert "Failed to send email" in str(exc_info.value)
        assert mock_smtp.send_message.call_count == MAX_RETRIES + 1

    @pytest.mark.asyncio
    async def test_retries_on_timeout_error(self, email_client: EmailClient) -> None:
        """Verify client retries on asyncio.TimeoutError."""
        mock_smtp = AsyncMock()
        mock_smtp.connect = AsyncMock()
        mock_smtp.starttls = AsyncMock()
        mock_smtp.login = AsyncMock()
        mock_smtp.quit = AsyncMock()
        mock_smtp.send_message = AsyncMock(
            side_effect=[asyncio.TimeoutError(), None]
        )

        with patch("app.integrations.email_client.aiosmtplib.SMTP", return_value=mock_smtp):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await email_client.send_email(
                    to="recipient@example.com",
                    subject="Timeout Test",
                    html_body="<p>Timeout</p>",
                )

        assert result is True

    @pytest.mark.asyncio
    async def test_retries_on_os_error(self, email_client: EmailClient) -> None:
        """Verify client retries on OSError (network failure)."""
        mock_smtp = AsyncMock()
        mock_smtp.connect = AsyncMock()
        mock_smtp.starttls = AsyncMock()
        mock_smtp.login = AsyncMock()
        mock_smtp.quit = AsyncMock()
        mock_smtp.send_message = AsyncMock(
            side_effect=[OSError("Connection refused"), None]
        )

        with patch("app.integrations.email_client.aiosmtplib.SMTP", return_value=mock_smtp):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await email_client.send_email(
                    to="recipient@example.com",
                    subject="OS Error Test",
                    html_body="<p>Network</p>",
                )

        assert result is True


class TestEmailClientDisabled:
    """Tests for graceful degradation when SMTP is disabled."""

    @pytest.mark.asyncio
    async def test_returns_false_when_disabled(
        self, disabled_email_client: EmailClient
    ) -> None:
        """Verify send returns False without raising when SMTP is not configured."""
        result = await disabled_email_client.send_email(
            to="recipient@example.com",
            subject="Should Not Send",
            html_body="<p>Nope</p>",
        )
        assert result is False

    def test_is_enabled_property_false(self, disabled_email_client: EmailClient) -> None:
        """Verify is_enabled reports False when SMTP is not configured."""
        assert disabled_email_client.is_enabled is False

    def test_is_enabled_property_true(self, email_client: EmailClient) -> None:
        """Verify is_enabled reports True when SMTP is configured."""
        assert email_client.is_enabled is True


class TestEmailClientMessageBuilding:
    """Tests for MIME message construction."""

    def test_message_includes_sender_name(self, email_client: EmailClient) -> None:
        """Verify From header includes display name when configured."""
        message = email_client._build_message(
            to="user@example.com",
            subject="Test",
            html_body="<p>Hi</p>",
        )
        assert "AI Coach" in message["From"]
        assert "noreply@example.com" in message["From"]

    def test_message_recipient_and_subject(self, email_client: EmailClient) -> None:
        """Verify To and Subject headers are set correctly."""
        message = email_client._build_message(
            to="user@test.com",
            subject="Important Subject",
            html_body="<p>Content</p>",
        )
        assert message["To"] == "user@test.com"
        assert message["Subject"] == "Important Subject"
