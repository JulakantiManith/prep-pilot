"""User and profile database models."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    """User model matching the users table schema."""

    id: UUID
    email: str
    full_name: str
    created_at: datetime
    updated_at: datetime


class Profile(BaseModel):
    """Profile model matching the profiles table schema."""

    id: UUID
    user_id: UUID
    target_role: Optional[str] = None
    experience_level: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    theme_preference: Optional[str] = None
    updated_at: datetime


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: str
    full_name: str


class ProfileUpdate(BaseModel):
    """Schema for updating a user profile."""

    target_role: Optional[str] = None
    experience_level: Optional[str] = None
    skills: Optional[list[str]] = None
    theme_preference: Optional[str] = None
