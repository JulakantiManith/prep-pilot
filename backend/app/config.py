"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # AI Services
    gemini_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    # Database
    database_url: str = ""

    # Security
    jwt_secret: str = ""

    # Application
    app_name: str = "AI Interview & Presentation Coach"
    app_version: str = "1.0.0"
    debug: bool = False

    # Domain configuration
    app_domain: str = ""
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    # CORS
    allowed_origins: str = ""

    # SMTP configuration
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_sender_email: str = ""
    smtp_sender_name: str = ""

    # Email deliverability check (optional startup validation)
    email_deliverability_check_enabled: bool = False

    # Email notifications (session completion emails)
    email_notifications_enabled: bool = True

    def get_resolved_frontend_url(self) -> str:
        """Resolve the frontend URL, stripping trailing slashes.

        Returns the frontend_url stripped of trailing slashes. If frontend_url
        is empty, returns the fallback "http://localhost:5173".

        Raises:
            ValueError: If non-empty value doesn't start with http:// or https://
        """
        fallback = "http://localhost:5173"
        url = self.frontend_url.strip() if self.frontend_url else ""

        if not url:
            return fallback

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ValueError(
                f"FRONTEND_URL must start with http:// or https://, got: {url}"
            )

        return url.rstrip("/")

    def get_resolved_backend_url(self) -> str:
        """Resolve the backend URL, stripping trailing slashes.

        Returns the backend_url stripped of trailing slashes. If backend_url
        is empty, returns the fallback "http://localhost:8000".

        Raises:
            ValueError: If non-empty value doesn't start with http:// or https://
        """
        fallback = "http://localhost:8000"
        url = self.backend_url.strip() if self.backend_url else ""

        if not url:
            return fallback

        if not url.startswith("http://") and not url.startswith("https://"):
            raise ValueError(
                f"BACKEND_URL must start with http:// or https://, got: {url}"
            )

        return url.rstrip("/")

    def get_parsed_origins(self) -> list[str]:
        """Parse comma-separated CORS origins.

        Splits allowed_origins by comma, trims whitespace, filters entries
        that don't start with http:// or https://, auto-includes the resolved
        frontend_url, and deduplicates.

        Returns:
            List of valid, deduplicated origin URLs.
        """
        origins: set[str] = set()

        # Auto-include the resolved frontend URL
        try:
            resolved_frontend = self.get_resolved_frontend_url()
            origins.add(resolved_frontend)
        except ValueError:
            # If frontend_url is invalid, use the default fallback
            origins.add("http://localhost:5173")

        # Parse comma-separated origins
        if self.allowed_origins:
            for entry in self.allowed_origins.split(","):
                origin = entry.strip()
                if origin and (
                    origin.startswith("http://") or origin.startswith("https://")
                ):
                    # Strip trailing slashes for consistency
                    origins.add(origin.rstrip("/"))

        return list(origins)

    def get_smtp_enabled(self) -> bool:
        """Check if SMTP is properly configured for sending emails.

        Returns True only when smtp_host is non-empty AND smtp_port > 0
        AND smtp_sender_email is non-empty.
        """
        return bool(
            self.smtp_host
            and self.smtp_port > 0
            and self.smtp_sender_email
        )

    def get_domain_mode(self) -> str:
        """Determine the domain configuration mode.

        Returns:
            "both" — when app_domain is set and frontend_url contains app_domain
            "custom_domain" — when app_domain is set but frontend_url doesn't contain app_domain
            "platform_url" — when app_domain is empty
        """
        if not self.app_domain:
            return "platform_url"

        if self.app_domain in self.frontend_url:
            return "both"

        return "custom_domain"


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
