"""Gemini API client with retry logic, timeout handling, and usage tracking.

Provides a resilient interface to Google's Gemini API for generating
interview questions and feedback. Implements exponential backoff retry
(1 retry) with a 45-second timeout per request.

Falls back to OpenRouter (openrouter/free) when Gemini is rate-limited,
unavailable, or returns errors after retry.

OPTIMIZATION: Minimizes API calls to stay within free-tier limits.
- Questions: 1 batch request for 10-15 questions (cached for 24h)
- Feedback: 1 request at session end with ALL data
- Target: Max 2 requests per session (1 with caching)

Requirements: 10.4 (feedback within 45s), 17.3 (retry once before failure)
"""

import asyncio
import json
import logging
from typing import Optional

import google.generativeai as genai
from google.api_core.exceptions import (
    GoogleAPIError,
    ResourceExhausted,
    ServiceUnavailable,
)

from app.config import get_settings
from app.integrations.openrouter_client import OpenRouterClient, OpenRouterClientError
from app.models.question import Question
from app.services.gemini_usage_tracker import (
    RequestType,
    usage_tracker,
)

logger = logging.getLogger(__name__)

# Timeout for each Gemini API call (seconds)
REQUEST_TIMEOUT = 45.0

# Retry configuration
MAX_RETRIES = 1
BASE_BACKOFF_SECONDS = 2.0

# Default batch size for question generation (optimized for single request)
DEFAULT_QUESTION_BATCH_SIZE = 10


class GeminiClientError(Exception):
    """Raised when Gemini API call fails after all retries."""

    pass


class GeminiClient:
    """Client for Google Gemini API with retry, timeout, and usage tracking.

    Implements:
    - 1 retry with exponential backoff on failure
    - 45-second timeout per request
    - Usage tracking for rate limit awareness
    - Structured logging of all API interactions

    Rate Limit Strategy:
    - Generate 10-15 questions in ONE batch request
    - Generate feedback in ONE request at session end
    - Questions cached for 24h to avoid repeated generation
    - Max 2 Gemini requests per interview session
    - With caching: max 1 request per session (feedback only)
    """

    def __init__(self) -> None:
        """Initialize the Gemini client with API key from settings."""
        settings = get_settings()
        self._api_key = settings.gemini_api_key
        self._model_name = "gemini-2.5-flash"
        self._configured = False

    @property
    def model_name(self) -> str:
        """Get the current model name."""
        return self._model_name

    def _ensure_configured(self) -> None:
        """Configure the Gemini SDK if not already done."""
        if not self._configured and self._api_key:
            genai.configure(api_key=self._api_key)
            self._configured = True

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for a string (rough: ~4 chars per token).

        Args:
            text: Input text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        return max(1, len(text) // 4)

    def _build_question_prompt(
        self,
        interview_type: str,
        role: str,
        topic: Optional[str] = None,
        difficulty: Optional[str] = None,
        num_questions: int = DEFAULT_QUESTION_BATCH_SIZE,
    ) -> str:
        """Build a structured prompt for batch question generation.

        Generates all questions in a single request to minimize API calls.

        Args:
            interview_type: Type of interview (hr, technical, behavioral, custom).
            role: Target job role.
            topic: Optional specific topic for technical interviews.
            difficulty: Optional difficulty level (beginner, intermediate, advanced).
            num_questions: Number of questions to generate (default: 10).

        Returns:
            Formatted prompt string for Gemini.
        """
        prompt_parts = [
            f"Generate exactly {num_questions} diverse interview questions for a {interview_type} interview.",
            f"Target role: {role}.",
        ]

        if topic:
            prompt_parts.append(f"Topic: {topic}.")
        if difficulty:
            prompt_parts.append(f"Difficulty level: {difficulty}.")

        prompt_parts.append(
            "\nIMPORTANT: These questions are for a VERBAL/SPOKEN interview practice session. "
            "The candidate will answer by speaking aloud, NOT by writing code. "
            "Do NOT generate coding challenges, implementation tasks, or questions that require "
            "writing code on a whiteboard. Instead, focus on conceptual understanding, "
            "explanation of concepts, design discussion, problem-solving approach, "
            "and real-world application questions that can be answered verbally."
            "\n\nEnsure questions cover different aspects and increase in complexity."
            "\nInclude a mix of conceptual, situational, and practical questions."
            "\nReturn the questions as a JSON array of objects with the following fields:"
            '\n- "text": the question text (string, required)'
            '\n- "topic": topic category (string or null)'
            '\n- "difficulty": difficulty level (string or null)'
            '\n- "follow_up": a suggested follow-up question (string or null)'
            "\n\nReturn ONLY the JSON array, no other text or markdown formatting."
        )

        return " ".join(prompt_parts)

    def _build_resume_question_prompt(
        self,
        resume_data: dict,
        role: str,
        num_questions: int = DEFAULT_QUESTION_BATCH_SIZE,
    ) -> str:
        """Build a prompt for resume-based question generation.

        Args:
            resume_data: Extracted resume data (skills, projects, experience, education).
            role: Target job role.
            num_questions: Number of questions to generate.

        Returns:
            Formatted prompt string for Gemini.
        """
        resume_summary = json.dumps(resume_data, indent=2)

        return (
            f"Generate exactly {num_questions} personalized interview questions "
            f"based on the following resume data for a {role} position.\n\n"
            f"Resume data:\n{resume_summary}\n\n"
            "Focus on the candidate's specific experience, skills, and projects. "
            "Ask questions that probe deeper into their claimed expertise.\n"
            "Include questions of varying difficulty and cover different aspects "
            "of their background.\n\n"
            "Return the questions as a JSON array of objects with the following fields:\n"
            '- "text": the question text (string, required)\n'
            '- "topic": topic category (string or null)\n'
            '- "difficulty": difficulty level (string or null)\n'
            '- "follow_up": a suggested follow-up question (string or null)\n\n'
            "Return ONLY the JSON array, no other text or markdown formatting."
        )

    async def _call_gemini(self, prompt: str) -> str:
        """Make a single API call to Gemini with timeout.

        Args:
            prompt: The prompt to send to Gemini.

        Returns:
            Raw text response from Gemini.

        Raises:
            asyncio.TimeoutError: If the request exceeds 45 seconds.
            GeminiClientError: If the API returns an error.
        """
        self._ensure_configured()

        if not self._api_key:
            raise GeminiClientError("Gemini API key is not configured")

        model = genai.GenerativeModel(self._model_name)

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=REQUEST_TIMEOUT,
            )
            if response.text:
                return response.text
            raise GeminiClientError("Gemini returned empty response")
        except asyncio.TimeoutError:
            raise
        except (GoogleAPIError, ResourceExhausted, ServiceUnavailable) as e:
            raise GeminiClientError(f"Gemini API error: {e}") from e

    async def _call_with_fallback(self, prompt: str) -> str:
        """Try Gemini with retry, then fall back to OpenRouter on failure.

        Used for: Resume parsing (Gemini is primary, OpenRouter is fallback).

        Flow:
        1. Try Gemini (with 1 retry + exponential backoff)
        2. If Gemini fails, try OpenRouter as fallback
        3. If both fail, raise GeminiClientError

        Args:
            prompt: The prompt to send.

        Returns:
            Raw text response from whichever provider succeeded.

        Raises:
            GeminiClientError: If both Gemini and OpenRouter fail.
        """
        last_error: Optional[Exception] = None

        # Try Gemini with retry
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await self._call_gemini(prompt)
                return response
            except (GeminiClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    backoff = BASE_BACKOFF_SECONDS * (2 ** attempt)
                    logger.warning(
                        "Gemini failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1, MAX_RETRIES + 1, backoff, str(e),
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.warning(
                        "Gemini failed after %d attempts: %s",
                        MAX_RETRIES + 1, str(e),
                    )

        # Fall back to OpenRouter
        fallback = OpenRouterClient()
        if not fallback.is_configured:
            logger.error(
                "Gemini failed and OpenRouter is not configured (no OPENROUTER_API_KEY). "
                "Cannot fall back."
            )
            raise GeminiClientError(
                f"Gemini unavailable and no fallback configured: {last_error}"
            )

        logger.info("Falling back to OpenRouter after Gemini failure")
        try:
            response = await fallback.generate(prompt)
            logger.info("OpenRouter fallback succeeded")
            return response
        except OpenRouterClientError as e:
            logger.error("OpenRouter fallback also failed: %s", str(e))
            raise GeminiClientError(
                f"Both Gemini and OpenRouter failed. "
                f"Gemini: {last_error} | OpenRouter: {e}"
            ) from e

    async def _call_openrouter_primary(self, prompt: str) -> str:
        """Call OpenRouter as the primary provider (no Gemini attempt).

        Used for: Question generation, AI feedback, relevance scoring.
        These tasks use OpenRouter/free directly to preserve Gemini quota
        for resume parsing.

        Args:
            prompt: The prompt to send.

        Returns:
            Raw text response from OpenRouter.

        Raises:
            GeminiClientError: If OpenRouter fails (wrapped for compatibility).
        """
        client = OpenRouterClient()
        if not client.is_configured:
            # If OpenRouter not configured, fall back to Gemini
            logger.warning(
                "OpenRouter not configured, falling back to Gemini for this request"
            )
            return await self._call_with_fallback(prompt)

        try:
            response = await client.generate(prompt)
            logger.debug("OpenRouter primary call succeeded")
            return response
        except OpenRouterClientError as e:
            logger.warning("OpenRouter primary failed: %s. Trying Gemini.", str(e))
            # Fall back to Gemini if OpenRouter fails
            try:
                return await self._call_gemini(prompt)
            except (GeminiClientError, asyncio.TimeoutError) as gemini_err:
                raise GeminiClientError(
                    f"OpenRouter failed ({e}) and Gemini also failed ({gemini_err})"
                ) from e

    def _parse_questions_response(
        self,
        response_text: str,
        interview_type: str,
        topic: Optional[str],
        difficulty: Optional[str],
    ) -> list[Question]:
        """Parse AI provider response into Question objects.

        Handles responses from both Gemini and OpenRouter. Robust to:
        - Markdown code fences (```json ... ```)
        - Extra text before/after JSON
        - Slight formatting variations

        Args:
            response_text: Raw response text from the AI provider.
            interview_type: Interview type for fallback field values.
            topic: Topic for fallback field values.
            difficulty: Difficulty for fallback field values.

        Returns:
            List of Question objects.

        Raises:
            GeminiClientError: If response cannot be parsed.
        """
        # Strip markdown code fences if present
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        # Try direct parse first
        data = None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # If direct parse fails, try to find a JSON array in the text
            # (handles cases where the provider adds extra text around the JSON)
            start_idx = text.find("[")
            end_idx = text.rfind("]")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                try:
                    data = json.loads(text[start_idx:end_idx + 1])
                except json.JSONDecodeError:
                    pass

        if data is None:
            raise GeminiClientError(
                f"Failed to parse AI response as JSON: {text[:200]}"
            )

        if not isinstance(data, list):
            raise GeminiClientError("Gemini response is not a JSON array")

        questions: list[Question] = []
        for item in data:
            if isinstance(item, dict) and "text" in item:
                questions.append(
                    Question(
                        text=item["text"],
                        topic=item.get("topic", topic),
                        difficulty=item.get("difficulty", difficulty),
                        interview_type=interview_type,
                        follow_up=item.get("follow_up"),
                    )
                )

        if not questions:
            raise GeminiClientError("Gemini response contained no valid questions")

        return questions

    async def generate_questions(
        self,
        interview_type: str,
        role: str,
        topic: Optional[str] = None,
        difficulty: Optional[str] = None,
        num_questions: int = DEFAULT_QUESTION_BATCH_SIZE,
        session_id: Optional[str] = None,
    ) -> list[Question]:
        """Generate interview questions via OpenRouter/free (primary).

        Uses OpenRouter as the primary provider for question generation
        to preserve Gemini quota for resume parsing. Falls back to Gemini
        if OpenRouter is unavailable.

        Args:
            interview_type: Type of interview (hr, technical, behavioral, custom).
            role: Target job role.
            topic: Optional specific topic.
            difficulty: Optional difficulty level.
            num_questions: Number of questions to generate (default: 10).
            session_id: Optional session ID for usage tracking.

        Returns:
            List of generated Question objects.

        Raises:
            GeminiClientError: If generation fails on all providers.
        """
        prompt = self._build_question_prompt(
            interview_type, role, topic, difficulty, num_questions
        )
        estimated_input_tokens = self._estimate_tokens(prompt)

        try:
            response_text = await self._call_openrouter_primary(prompt)
            questions = self._parse_questions_response(
                response_text, interview_type, topic, difficulty
            )

            # Track successful request
            estimated_output_tokens = self._estimate_tokens(response_text)
            usage_tracker.record_request(
                request_type=RequestType.QUESTION_GENERATION,
                success=True,
                session_id=session_id,
                estimated_input_tokens=estimated_input_tokens,
                estimated_output_tokens=estimated_output_tokens,
            )

            logger.info(
                "Generated %d questions (type=%s, role=%s, topic=%s)",
                len(questions),
                interview_type,
                role,
                topic,
            )
            return questions

        except GeminiClientError as e:
            # Track failed request
            usage_tracker.record_request(
                request_type=RequestType.QUESTION_GENERATION,
                success=False,
                session_id=session_id,
                estimated_input_tokens=estimated_input_tokens,
                error=str(e),
            )
            raise

    async def generate_resume_questions(
        self,
        resume_data: dict,
        role: str,
        num_questions: int = DEFAULT_QUESTION_BATCH_SIZE,
        session_id: Optional[str] = None,
    ) -> list[Question]:
        """Generate personalized questions based on resume data.

        Uses OpenRouter/free as primary provider for question generation.
        Falls back to Gemini if OpenRouter fails.

        Args:
            resume_data: Extracted resume data dict.
            role: Target job role.
            num_questions: Number of questions to generate.
            session_id: Optional session ID for usage tracking.

        Returns:
            List of personalized Question objects.

        Raises:
            GeminiClientError: If generation fails on all providers.
        """
        prompt = self._build_resume_question_prompt(resume_data, role, num_questions)
        estimated_input_tokens = self._estimate_tokens(prompt)

        try:
            response_text = await self._call_openrouter_primary(prompt)
            questions = self._parse_questions_response(
                response_text, "resume_based", None, None
            )

            # Track successful request
            estimated_output_tokens = self._estimate_tokens(response_text)
            usage_tracker.record_request(
                request_type=RequestType.RESUME_QUESTIONS,
                success=True,
                session_id=session_id,
                estimated_input_tokens=estimated_input_tokens,
                estimated_output_tokens=estimated_output_tokens,
            )

            return questions

        except GeminiClientError as e:
            # Track failed request
            usage_tracker.record_request(
                request_type=RequestType.RESUME_QUESTIONS,
                success=False,
                session_id=session_id,
                estimated_input_tokens=estimated_input_tokens,
                error=str(e),
            )
            raise
