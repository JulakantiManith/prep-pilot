"""Authentication API routes."""

import logging

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.api.schemas.auth_schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.dependencies import CurrentUserDep
from app.services.auth_service import get_auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(request: RegisterRequest):
    """Register a new user account.

    Creates a new user with the provided full name, email, and password.
    Sends an email verification link upon successful registration.
    """
    auth_service = get_auth_service()
    result = auth_service.register(
        full_name=request.full_name,
        email=request.email,
        password=request.password,
    )
    return AuthResponse(**result)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with credentials",
)
async def login(request: LoginRequest):
    """Authenticate a user with email and password.

    Returns a session token on success. Returns a generic error
    message on failure to prevent credential enumeration.
    """
    auth_service = get_auth_service()
    result = auth_service.login(
        email=request.email,
        password=request.password,
    )
    return AuthResponse(**result)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout current user",
)
async def logout(
    current_user_id: CurrentUserDep,
    authorization: str | None = Header(default=None),
):
    """Logout the currently authenticated user.

    Invalidates the current session token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = authorization.removeprefix("Bearer ").strip()
    auth_service = get_auth_service()
    auth_service.logout(access_token=token)
    return MessageResponse(message="Successfully logged out")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
)
async def forgot_password(request: ForgotPasswordRequest):
    """Request a password reset email.

    Always returns the same success response regardless of whether
    the email is registered, to prevent email enumeration.
    """
    auth_service = get_auth_service()
    auth_service.forgot_password(email=request.email)
    return MessageResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with token",
)
async def reset_password(request: ResetPasswordRequest):
    """Reset the user's password using a valid reset token.

    The token is obtained from the password reset email link.
    """
    auth_service = get_auth_service()
    auth_service.reset_password(
        token=request.token,
        new_password=request.new_password,
    )
    return MessageResponse(message="Password has been reset successfully")
