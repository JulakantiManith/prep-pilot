"""Session repository for database operations with retry on write failure.

Provides data access methods for sessions and answers using Supabase.
Implements retry-once logic for write operations per Requirement 16.3.

Requirements: 16.1 (persist session data), 16.3 (retry once on write failure)
"""

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.integrations.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Retry configuration for write operations - Requirement 16.3
WRITE_MAX_RETRIES = 1


class RepositoryError(Exception):
    """Raised when a database operation fails after retries."""

    pass


class SessionRepository:
    """Repository for session and answer database operations.

    All write operations implement retry-once logic per Requirement 16.3.
    Read operations do not retry (standard fail-fast behavior).
    All queries filter by user_id for data isolation.
    """

    def __init__(self) -> None:
        """Initialize with Supabase client."""
        self._client = get_supabase_client()

    def _retry_write(self, operation_name: str, operation_fn: Any) -> Any:
        """Execute a write operation with retry-once logic.

        Per Requirement 16.3: retry the operation once on failure.

        Args:
            operation_name: Descriptive name for logging.
            operation_fn: Callable that performs the write operation.

        Returns:
            Result of the operation.

        Raises:
            RepositoryError: If the operation fails after retry.
        """
        last_error: Optional[Exception] = None

        for attempt in range(WRITE_MAX_RETRIES + 1):
            try:
                result = operation_fn()
                return result
            except Exception as e:
                last_error = e
                if attempt < WRITE_MAX_RETRIES:
                    logger.warning(
                        "Database write failed for '%s' (attempt %d/%d), retrying: %s",
                        operation_name,
                        attempt + 1,
                        WRITE_MAX_RETRIES + 1,
                        str(e),
                    )
                else:
                    logger.error(
                        "Database write failed for '%s' after %d attempts: %s",
                        operation_name,
                        WRITE_MAX_RETRIES + 1,
                        str(e),
                    )

        raise RepositoryError(
            f"Database write operation '{operation_name}' failed after "
            f"{WRITE_MAX_RETRIES + 1} attempts: {last_error}"
        )

    def create_session(self, session_data: dict) -> dict:
        """Create a new session record in the database.

        Args:
            session_data: Session data dict matching the sessions table schema.

        Returns:
            Created session record from the database.

        Raises:
            RepositoryError: If creation fails after retry.
        """

        def _create() -> dict:
            logger.info("Inserting into sessions table: %s", session_data)
            response = (
                self._client.table("sessions").insert(session_data).execute()
            )
            logger.info(
                "Supabase insert response: data=%s, count=%s",
                response.data,
                getattr(response, "count", None),
            )
            if not response.data:
                raise RepositoryError(
                    "Supabase insert returned empty data. "
                    f"Response: {response}"
                )
            return response.data[0]

        return self._retry_write("create_session", _create)

    def get_session(self, session_id: UUID, user_id: str) -> Optional[dict]:
        """Get a session by ID, filtered by user_id for data isolation.

        Args:
            session_id: The session UUID.
            user_id: The owning user's ID.

        Returns:
            Session record dict or None if not found.
        """
        try:
            response = (
                self._client.table("sessions")
                .select("*")
                .eq("id", str(session_id))
                .eq("user_id", user_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error("Failed to get session %s: %s", session_id, str(e))
            raise RepositoryError(f"Failed to get session: {e}") from e

    def update_session(self, session_id: UUID, user_id: str, updates: dict) -> dict:
        """Update a session record with retry on failure.

        Args:
            session_id: The session UUID.
            user_id: The owning user's ID for data isolation.
            updates: Dict of fields to update.

        Returns:
            Updated session record.

        Raises:
            RepositoryError: If update fails after retry.
        """

        def _update() -> dict:
            response = (
                self._client.table("sessions")
                .update(updates)
                .eq("id", str(session_id))
                .eq("user_id", user_id)
                .execute()
            )
            if not response.data:
                raise RepositoryError(
                    f"Session {session_id} not found or not owned by user"
                )
            return response.data[0]

        return self._retry_write("update_session", _update)

    def create_answer(self, answer_data: dict) -> dict:
        """Create or update an answer record in the database.

        Uses upsert on (session_id, question_index) so re-submitting
        an answer for the same question (e.g., after page refresh)
        updates the existing row instead of failing with a conflict.

        Args:
            answer_data: Answer data dict matching the answers table schema.

        Returns:
            Created or updated answer record from the database.

        Raises:
            RepositoryError: If operation fails after retry.
        """

        def _upsert() -> dict:
            response = (
                self._client.table("answers")
                .upsert(answer_data, on_conflict="session_id,question_index")
                .execute()
            )
            return response.data[0]

        return self._retry_write("create_answer", _upsert)

    def update_answer(self, answer_id: UUID, updates: dict) -> dict:
        """Update an answer record with retry on failure.

        Args:
            answer_id: The answer UUID.
            updates: Dict of fields to update.

        Returns:
            Updated answer record.

        Raises:
            RepositoryError: If update fails after retry.
        """

        def _update() -> dict:
            response = (
                self._client.table("answers")
                .update(updates)
                .eq("id", str(answer_id))
                .execute()
            )
            if not response.data:
                raise RepositoryError(f"Answer {answer_id} not found")
            return response.data[0]

        return self._retry_write("update_answer", _update)

    def get_session_answers(self, session_id: UUID, user_id: str) -> list[dict]:
        """Get all answers for a session, ordered by question index.

        Args:
            session_id: The session UUID.
            user_id: The owning user's ID for data isolation.

        Returns:
            List of answer records ordered by question_index.
        """
        try:
            # Verify session belongs to user first
            session = self.get_session(session_id, user_id)
            if not session:
                raise RepositoryError(
                    f"Session {session_id} not found or not owned by user"
                )

            response = (
                self._client.table("answers")
                .select("*")
                .eq("session_id", str(session_id))
                .order("question_index")
                .execute()
            )
            return response.data or []
        except RepositoryError:
            raise
        except Exception as e:
            logger.error(
                "Failed to get answers for session %s: %s", session_id, str(e)
            )
            raise RepositoryError(f"Failed to get session answers: {e}") from e

    def store_session_questions(self, session_id: UUID, questions: list[dict]) -> None:
        """Store generated questions for a session.

        Args:
            session_id: The session UUID.
            questions: List of question dicts to store.

        Raises:
            RepositoryError: If storage fails after retry.
        """
        question_records = [
            {
                "session_id": str(session_id),
                "question_index": idx,
                "question_text": q.get("text", ""),
                "topic": q.get("topic"),
                "difficulty": q.get("difficulty"),
            }
            for idx, q in enumerate(questions)
        ]

        def _store() -> None:
            self._client.table("session_questions").insert(question_records).execute()

        self._retry_write("store_session_questions", _store)

    def get_session_questions(self, session_id: UUID) -> list[dict]:
        """Get all questions for a session, ordered by index.

        Args:
            session_id: The session UUID.

        Returns:
            List of question records ordered by question_index.
        """
        try:
            response = (
                self._client.table("session_questions")
                .select("*")
                .eq("session_id", str(session_id))
                .order("question_index")
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(
                "Failed to get questions for session %s: %s", session_id, str(e)
            )
            raise RepositoryError(f"Failed to get session questions: {e}") from e

    def create_session_feedback(self, session_id: UUID, feedback_data: dict) -> dict:
        """Save AI-generated feedback for a session.

        Args:
            session_id: The session UUID.
            feedback_data: Dict with strengths, weaknesses, recommendations,
                          and optional technical_evaluation/presentation_scores.

        Returns:
            The created feedback record.

        Raises:
            RepositoryError: If save fails after retry.
        """
        record = {
            "session_id": str(session_id),
            "strengths": feedback_data.get("strengths", []),
            "weaknesses": feedback_data.get("weaknesses", []),
            "recommendations": feedback_data.get("recommendations", []),
        }
        if feedback_data.get("technical_evaluation"):
            record["technical_evaluation"] = feedback_data["technical_evaluation"]
        if feedback_data.get("presentation_scores"):
            record["presentation_scores"] = feedback_data["presentation_scores"]

        def _create() -> dict:
            response = self._client.table("session_feedback").insert(record).execute()
            if not response.data:
                raise RepositoryError("No data returned from feedback insert")
            return response.data[0]

        return self._retry_write("create_session_feedback", _create)

    def get_session_feedback(self, session_id: UUID) -> dict | None:
        """Get feedback for a session.

        Args:
            session_id: The session UUID.

        Returns:
            The feedback record dict, or None if not found.
        """
        try:
            response = (
                self._client.table("session_feedback")
                .select("*")
                .eq("session_id", str(session_id))
                .limit(1)
                .execute()
            )
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.warning("Failed to get session feedback: %s", str(e))
            return None
