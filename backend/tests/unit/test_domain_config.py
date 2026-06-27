"""Unit tests for domain configuration and auth redirect URL construction.

Tests verify that URLs use the production domain from environment settings,
and that all email templates render correctly with test data.

Requirements: 1.1, 1.4, 1.5, 17.2
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import Settings


class TestResolvedFrontendUrl:
    """Tests for get_resolved_frontend_url used in auth redirect URLs."""

    def test_returns_configured_frontend_url(self) -> None:
        """Verify production domain is returned when configured."""
        settings = Settings(frontend_url="https://app.interviewcoach.com")
        assert settings.get_resolved_frontend_url() == "https://app.interviewcoach.com"

    def test_strips_trailing_slash(self) -> None:
        """Verify trailing slashes are stripped from frontend URL."""
        settings = Settings(frontend_url="https://app.interviewcoach.com/")
        assert settings.get_resolved_frontend_url() == "https://app.interviewcoach.com"

    def test_strips_multiple_trailing_slashes(self) -> None:
        """Verify multiple trailing slashes are stripped."""
        settings = Settings(frontend_url="https://app.example.com///")
        assert settings.get_resolved_frontend_url() == "https://app.example.com"

    def test_returns_fallback_when_empty(self) -> None:
        """Verify fallback localhost URL when frontend_url is empty."""
        settings = Settings(frontend_url="")
        assert settings.get_resolved_frontend_url() == "http://localhost:5173"

    def test_raises_on_invalid_scheme(self) -> None:
        """Verify ValueError raised for URLs without http/https scheme."""
        settings = Settings(frontend_url="ftp://invalid.com")
        with pytest.raises(ValueError, match="must start with http://"):
            settings.get_resolved_frontend_url()

    def test_uses_https_for_production(self) -> None:
        """Verify production domain uses HTTPS scheme."""
        settings = Settings(frontend_url="https://coach.production.com")
        url = settings.get_resolved_frontend_url()
        assert url.startswith("https://")

    def test_http_allowed_for_development(self) -> None:
        """Verify http:// is allowed (for local development)."""
        settings = Settings(frontend_url="http://localhost:3000")
        url = settings.get_resolved_frontend_url()
        assert url == "http://localhost:3000"


class TestResolvedBackendUrl:
    """Tests for get_resolved_backend_url used in API callbacks."""

    def test_returns_configured_backend_url(self) -> None:
        """Verify production backend URL is returned when configured."""
        settings = Settings(backend_url="https://api.interviewcoach.com")
        assert settings.get_resolved_backend_url() == "https://api.interviewcoach.com"

    def test_strips_trailing_slash(self) -> None:
        """Verify trailing slashes are stripped from backend URL."""
        settings = Settings(backend_url="https://api.example.com/")
        assert settings.get_resolved_backend_url() == "https://api.example.com"

    def test_returns_fallback_when_empty(self) -> None:
        """Verify fallback localhost URL when backend_url is empty."""
        settings = Settings(backend_url="")
        assert settings.get_resolved_backend_url() == "http://localhost:8000"


class TestSmtpEnabled:
    """Tests for get_smtp_enabled configuration check."""

    def test_enabled_with_full_config(self) -> None:
        """SMTP enabled when host, port > 0, and sender email all set."""
        settings = Settings(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_sender_email="noreply@example.com",
        )
        assert settings.get_smtp_enabled() is True

    def test_disabled_without_host(self) -> None:
        """SMTP disabled when host is empty."""
        settings = Settings(
            smtp_host="",
            smtp_port=587,
            smtp_sender_email="noreply@example.com",
        )
        assert settings.get_smtp_enabled() is False

    def test_disabled_without_port(self) -> None:
        """SMTP disabled when port is 0."""
        settings = Settings(
            smtp_host="smtp.example.com",
            smtp_port=0,
            smtp_sender_email="noreply@example.com",
        )
        assert settings.get_smtp_enabled() is False

    def test_disabled_without_sender_email(self) -> None:
        """SMTP disabled when sender email is empty."""
        settings = Settings(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_sender_email="",
        )
        assert settings.get_smtp_enabled() is False


class TestDomainMode:
    """Tests for get_domain_mode which determines URL construction strategy."""

    def test_platform_url_mode_when_no_app_domain(self) -> None:
        """Returns 'platform_url' when app_domain is empty."""
        settings = Settings(app_domain="", frontend_url="https://myapp.vercel.app")
        assert settings.get_domain_mode() == "platform_url"

    def test_both_mode_when_app_domain_in_frontend_url(self) -> None:
        """Returns 'both' when app_domain matches frontend_url."""
        settings = Settings(
            app_domain="interviewcoach.com",
            frontend_url="https://app.interviewcoach.com",
        )
        assert settings.get_domain_mode() == "both"

    def test_custom_domain_mode_when_app_domain_differs(self) -> None:
        """Returns 'custom_domain' when app_domain is set but not in frontend_url."""
        settings = Settings(
            app_domain="interviewcoach.com",
            frontend_url="https://myapp.vercel.app",
        )
        assert settings.get_domain_mode() == "custom_domain"


class TestAuthRedirectUrlConstruction:
    """Tests verifying auth redirect URLs use the production domain from env."""

    def test_verification_redirect_uses_frontend_url(self) -> None:
        """Auth verification redirect should use resolved frontend URL."""
        settings = Settings(frontend_url="https://app.interviewcoach.com")
        base_url = settings.get_resolved_frontend_url()
        verify_url = f"{base_url}/verify-email"
        assert verify_url == "https://app.interviewcoach.com/verify-email"

    def test_password_reset_redirect_uses_frontend_url(self) -> None:
        """Password reset redirect should use resolved frontend URL."""
        settings = Settings(frontend_url="https://app.interviewcoach.com")
        base_url = settings.get_resolved_frontend_url()
        reset_url = f"{base_url}/reset-password"
        assert reset_url == "https://app.interviewcoach.com/reset-password"

    def test_session_report_url_uses_frontend_url(self) -> None:
        """Session report CTA URL should use resolved frontend URL."""
        settings = Settings(frontend_url="https://app.interviewcoach.com")
        base_url = settings.get_resolved_frontend_url()
        session_id = "test-session-123"
        report_url = f"{base_url}/history/{session_id}"
        assert report_url == "https://app.interviewcoach.com/history/test-session-123"


class TestEmailTemplateRendering:
    """Tests verifying all email templates render correctly with test data."""

    TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "templates" / "emails"

    def test_session_complete_template_no_broken_placeholders(self) -> None:
        """Verify session_complete_email.html has no missing variable patterns."""
        template_path = self.TEMPLATES_DIR / "session_complete_email.html"
        content = template_path.read_text(encoding="utf-8")

        # Replace all known placeholders
        replacements = {
            "{{ session_type }}": "HR Interview",
            "{{ session_date }}": "June 15, 2024",
            "{{ overall_score }}": "85",
            "{{ score_color }}": "#16a34a",
            "{{ strength_1 }}": "Clear communication",
            "{{ strength_2 }}": "Good structure",
            "{{ improvement_area }}": "Pacing",
            "{{ report_url }}": "https://app.example.com/history/123",
        }

        rendered = content
        for placeholder, value in replacements.items():
            rendered = rendered.replace(placeholder, value)

        # No remaining {{ ... }} placeholders
        assert "{{ " not in rendered
        assert " }}" not in rendered

        # Verify links are not broken
        assert "https://app.example.com/history/123" in rendered
        assert 'href=""' not in rendered

    def test_verification_email_template_no_broken_placeholders(self) -> None:
        """Verify verification_email.html has only Supabase Go template vars."""
        template_path = self.TEMPLATES_DIR / "verification_email.html"
        content = template_path.read_text(encoding="utf-8")

        # Supabase Go template variables use {{ .VarName }} syntax
        # After substitution by Supabase, there should be no unresolved vars
        replacements = {
            "{{ .ConfirmationURL }}": "https://app.example.com/verify?token=abc",
            "{{ .Token }}": "abc123",
            "{{ .SiteURL }}": "https://app.example.com",
            "{{ .Email }}": "user@example.com",
        }

        rendered = content
        for placeholder, value in replacements.items():
            rendered = rendered.replace(placeholder, value)

        # No remaining {{ ... }} template variables
        assert "{{ " not in rendered
        assert " }}" not in rendered

        # Verify links are valid
        assert "https://app.example.com/verify?token=abc" in rendered
        assert "https://app.example.com" in rendered

    def test_password_reset_template_no_broken_placeholders(self) -> None:
        """Verify password_reset_email.html has no missing variables."""
        template_path = self.TEMPLATES_DIR / "password_reset_email.html"
        content = template_path.read_text(encoding="utf-8")

        replacements = {
            "{{ .ConfirmationURL }}": "https://app.example.com/reset?token=xyz",
            "{{ .Token }}": "xyz789",
            "{{ .SiteURL }}": "https://app.example.com",
            "{{ .Email }}": "user@example.com",
        }

        rendered = content
        for placeholder, value in replacements.items():
            rendered = rendered.replace(placeholder, value)

        assert "{{ " not in rendered
        assert " }}" not in rendered
        assert "https://app.example.com/reset?token=xyz" in rendered

    def test_magic_link_template_no_broken_placeholders(self) -> None:
        """Verify magic_link_email.html has no missing variables."""
        template_path = self.TEMPLATES_DIR / "magic_link_email.html"
        content = template_path.read_text(encoding="utf-8")

        replacements = {
            "{{ .ConfirmationURL }}": "https://app.example.com/magic?token=mlk",
            "{{ .Token }}": "mlk456",
            "{{ .SiteURL }}": "https://app.example.com",
            "{{ .Email }}": "user@example.com",
        }

        rendered = content
        for placeholder, value in replacements.items():
            rendered = rendered.replace(placeholder, value)

        assert "{{ " not in rendered
        assert " }}" not in rendered
        assert "https://app.example.com/magic?token=mlk" in rendered

    def test_otp_template_no_broken_placeholders(self) -> None:
        """Verify otp_email.html has no missing variables."""
        template_path = self.TEMPLATES_DIR / "otp_email.html"
        content = template_path.read_text(encoding="utf-8")

        replacements = {
            "{{ .Token }}": "482910",
            "{{ .SiteURL }}": "https://app.example.com",
            "{{ .Email }}": "user@example.com",
        }

        rendered = content
        for placeholder, value in replacements.items():
            rendered = rendered.replace(placeholder, value)

        assert "{{ " not in rendered
        assert " }}" not in rendered
        assert "482910" in rendered

    def test_all_templates_contain_valid_html_structure(self) -> None:
        """Verify all templates have proper DOCTYPE, html, head, body tags."""
        template_files = [
            "session_complete_email.html",
            "verification_email.html",
            "password_reset_email.html",
            "magic_link_email.html",
            "otp_email.html",
        ]

        for filename in template_files:
            path = self.TEMPLATES_DIR / filename
            content = path.read_text(encoding="utf-8")

            assert "<!DOCTYPE html>" in content, f"{filename} missing DOCTYPE"
            assert "<html" in content, f"{filename} missing <html>"
            assert "</html>" in content, f"{filename} missing </html>"
            assert "<head>" in content, f"{filename} missing <head>"
            assert "</head>" in content, f"{filename} missing </head>"
            assert "<body" in content, f"{filename} missing <body>"
            assert "</body>" in content, f"{filename} missing </body>"

    def test_all_templates_have_responsive_viewport_meta(self) -> None:
        """Verify all templates include viewport meta for mobile responsiveness."""
        template_files = [
            "session_complete_email.html",
            "verification_email.html",
            "password_reset_email.html",
            "magic_link_email.html",
            "otp_email.html",
        ]

        for filename in template_files:
            path = self.TEMPLATES_DIR / filename
            content = path.read_text(encoding="utf-8")

            assert "viewport" in content, f"{filename} missing viewport meta"
            assert "width=device-width" in content, f"{filename} missing width=device-width"

    def test_all_templates_support_dark_mode(self) -> None:
        """Verify all templates include prefers-color-scheme dark mode styles."""
        template_files = [
            "session_complete_email.html",
            "verification_email.html",
            "password_reset_email.html",
            "magic_link_email.html",
            "otp_email.html",
        ]

        for filename in template_files:
            path = self.TEMPLATES_DIR / filename
            content = path.read_text(encoding="utf-8")

            assert "prefers-color-scheme: dark" in content, (
                f"{filename} missing dark mode support"
            )
