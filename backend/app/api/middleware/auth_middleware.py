"""JWT authentication middleware for verifying Supabase tokens."""

import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Supabase uses HS256 for JWT signing
ALGORITHM = "HS256"


def _decode_token(token: str, settings: Settings) -> dict:
    """Decode and verify a JWT token using the configured secret.

    Args:
        token: The raw JWT token string.
        settings: Application settings containing the JWT secret.

    Returns:
        The decoded token payload as a dictionary.

    Raises:
        HTTPException: If the token is invalid, expired, or cannot be decoded.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},
        )
        return payload
    except JWTError as e:
        logger.warning("JWT verification failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> str:
    """Extract and validate user ID from JWT authorization header.

    Verifies the JWT token via Supabase's JWT secret and extracts
    the 'sub' claim as the authenticated user's ID.

    Args:
        authorization: The Authorization header value (Bearer <token>).
        settings: Application settings injected via dependency.

    Returns:
        The authenticated user's ID (UUID string from Supabase Auth).

    Raises:
        HTTPException: 401 if the token is missing, malformed, or invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_token(token, settings)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain a valid user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id
