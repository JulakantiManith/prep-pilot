"""Common FastAPI dependencies for dependency injection."""

from typing import Annotated

from fastapi import Depends

from app.api.middleware.auth_middleware import get_current_user_id
from app.config import Settings, get_settings


def get_current_settings() -> Settings:
    """Dependency to provide application settings."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_current_settings)]

CurrentUserDep = Annotated[str, Depends(get_current_user_id)]
