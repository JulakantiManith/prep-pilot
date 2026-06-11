"""Common FastAPI dependencies for dependency injection."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


def get_current_settings() -> Settings:
    """Dependency to provide application settings."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_current_settings)]


async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_current_settings),
) -> str:
    """Extract and validate user ID from JWT authorization header.

    This is a placeholder that will be fully implemented in the auth middleware task.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )
    # Full JWT verification will be implemented in task 1.6
    token = authorization.removeprefix("Bearer ")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    # Placeholder: return token subject (will be replaced with proper JWT decode)
    return token


CurrentUserDep = Annotated[str, Depends(get_current_user_id)]
