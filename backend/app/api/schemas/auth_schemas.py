"""Pydantic schemas for authentication endpoints."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


def _validate_password_strength(password: str) -> str:
    """Validate password meets strength requirements.

    Requires at least 8 characters with uppercase, lowercase, and digit.
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    return password


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    full_name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, max_length=128, description="User's password")

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Ensure password meets strength requirements."""
        return _validate_password_strength(v)

    @field_validator("full_name")
    @classmethod
    def full_name_not_blank(cls, v: str) -> str:
        """Ensure full name is not just whitespace."""
        if not v.strip():
            raise ValueError("Full name cannot be blank")
        return v.strip()


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=1, description="User's password")


class ForgotPasswordRequest(BaseModel):
    """Request schema for forgot password."""

    email: EmailStr = Field(..., description="Email address for password reset")


class ResetPasswordRequest(BaseModel):
    """Request schema for password reset."""

    token: str = Field(..., min_length=1, description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Ensure new password meets strength requirements."""
        return _validate_password_strength(v)


class UserInfo(BaseModel):
    """User information returned in auth responses."""

    id: str
    email: str
    full_name: str | None = None


class AuthResponse(BaseModel):
    """Response schema for successful authentication."""

    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
