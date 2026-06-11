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
    whisper_api_key: str = ""

    # Database
    database_url: str = ""

    # Security
    jwt_secret: str = ""

    # Application
    app_name: str = "AI Interview & Presentation Coach"
    app_version: str = "1.0.0"
    debug: bool = False

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
