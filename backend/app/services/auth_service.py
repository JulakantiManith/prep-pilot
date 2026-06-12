"""Authentication service wrapping Supabase Auth methods."""

import logging

from fastapi import HTTPException, status

from app.integrations.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class AuthService:
    """Service layer for authentication operations using Supabase Auth."""

    def __init__(self):
        self._client = get_supabase_client()

    def register(self, full_name: str, email: str, password: str) -> dict:
        """Register a new user account.

        Creates the user in Supabase Auth which also sends a verification email.

        Args:
            full_name: User's full name.
            email: User's email address.
            password: User's chosen password.

        Returns:
            Dictionary with access_token, token_type, and user info.

        Raises:
            HTTPException: 400 if registration fails (e.g., email already exists).
        """
        try:
            response = self._client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": {"full_name": full_name}},
                }
            )

            if not response.user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Registration failed. Please try again.",
                )

            # Extract session info if available (auto-confirm enabled)
            access_token = ""
            if response.session:
                access_token = response.session.access_token

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": str(response.user.id),
                    "email": response.user.email or email,
                    "full_name": full_name,
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Registration failed for email %s: %s", email, str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed. The email may already be registered.",
            ) from e

    def login(self, email: str, password: str) -> dict:
        """Authenticate a user with email and password.

        Args:
            email: User's email address.
            password: User's password.

        Returns:
            Dictionary with access_token, token_type, and user info.

        Raises:
            HTTPException: 401 with generic message if credentials are invalid.
        """
        try:
            response = self._client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )

            if not response.user or not response.session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                )

            user_meta = response.user.user_metadata or {}

            return {
                "access_token": response.session.access_token,
                "token_type": "bearer",
                "user": {
                    "id": str(response.user.id),
                    "email": response.user.email or email,
                    "full_name": user_meta.get("full_name"),
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Login failed for email %s: %s", email, str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            ) from e

    def logout(self, access_token: str) -> None:
        """Invalidate the current user session.

        Args:
            access_token: The JWT access token to invalidate.

        Raises:
            HTTPException: 500 if logout fails unexpectedly.
        """
        try:
            self._client.auth.admin.sign_out(access_token)
        except Exception as e:
            logger.error("Logout failed: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed. Please try again.",
            ) from e

    def forgot_password(self, email: str) -> None:
        """Send a password reset email.

        Always succeeds regardless of whether the email is registered,
        to prevent email enumeration attacks.

        Args:
            email: Email address to send the reset link to.
        """
        try:
            self._client.auth.reset_password_for_email(email)
        except Exception as e:
            # Silently catch all errors to prevent email enumeration
            logger.debug("Forgot password request for %s: %s", email, str(e))

    def reset_password(self, token: str, new_password: str) -> None:
        """Reset a user's password using a valid reset token.

        Args:
            token: The password reset token from the email link.
            new_password: The new password to set.

        Raises:
            HTTPException: 400 if the token is invalid or expired.
        """
        try:
            # Verify the token and get a session
            session_response = self._client.auth.verify_otp(
                {"token_hash": token, "type": "recovery"}
            )

            if not session_response.user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired reset link",
                )

            # Update the user's password
            self._client.auth.admin.update_user_by_id(
                str(session_response.user.id),
                {"password": new_password},
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Password reset failed: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset link",
            ) from e


def get_auth_service() -> AuthService:
    """Factory function for AuthService dependency injection."""
    return AuthService()
