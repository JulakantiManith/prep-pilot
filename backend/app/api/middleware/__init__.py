"""Middleware components for the API layer."""

from app.api.middleware.auth_middleware import get_current_user_id
from app.api.middleware.error_handler import register_exception_handlers

__all__ = ["get_current_user_id", "register_exception_handlers"]
