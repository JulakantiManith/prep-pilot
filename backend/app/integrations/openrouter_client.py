"""OpenRouter API client for AI text generation fallback.

Uses OpenRouter's free router (openrouter/free) as a fallback when Gemini
is rate-limited or unavailable. Communicates via the OpenAI-compatible
chat completions endpoint.

Used as a fallback provider for: question generation, feedback generation,
and resume parsing.
"""

import asyncio
import logging
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Timeout for each OpenRouter API call (seconds)
REQUEST_TIMEOUT = 45.0

# OpenRouter API endpoint
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model to use (free-only router — ensures no paid models are used)
OPENROUTER_MODEL = "openrouter/free"


class OpenRouterClientError(Exception):
    """Raised when OpenRouter API call fails."""

    pass


class OpenRouterClient:
    """Client for OpenRouter API using the free router model.

    Sends prompts via the OpenAI-compatible chat completions endpoint.
    Used as a fallback when Gemini is unavailable or rate-limited.
    """

    def __init__(self) -> None:
        """Initialize the OpenRouter client with API key from settings."""
        settings = get_settings()
        self._api_key = settings.openrouter_api_key

    @property
    def is_configured(self) -> bool:
        """Check if the OpenRouter API key is set."""
        return bool(self._api_key)

    async def generate(self, prompt: str) -> str:
        """Send a prompt to OpenRouter and return the text response.

        Args:
            prompt: The prompt to send.

        Returns:
            Generated text response.

        Raises:
            OpenRouterClientError: If the API call fails or returns no content.
        """
        if not self._api_key:
            raise OpenRouterClientError("OpenRouter API key is not configured")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "AI Interview Coach",
        }

        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(
                    OPENROUTER_BASE_URL,
                    headers=headers,
                    json=payload,
                )

            if response.status_code == 429:
                raise OpenRouterClientError(
                    "OpenRouter rate limited (429)"
                )

            if response.status_code >= 500:
                raise OpenRouterClientError(
                    f"OpenRouter server error ({response.status_code})"
                )

            if response.status_code != 200:
                raise OpenRouterClientError(
                    f"OpenRouter returned status {response.status_code}: "
                    f"{response.text[:200]}"
                )

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise OpenRouterClientError("OpenRouter returned no choices")

            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise OpenRouterClientError("OpenRouter returned empty content")

            return content

        except httpx.TimeoutException as e:
            raise OpenRouterClientError(
                f"OpenRouter request timed out after {REQUEST_TIMEOUT}s"
            ) from e
        except httpx.HTTPError as e:
            raise OpenRouterClientError(
                f"OpenRouter HTTP error: {e}"
            ) from e
        except OpenRouterClientError:
            raise
        except Exception as e:
            raise OpenRouterClientError(
                f"Unexpected error calling OpenRouter: {e}"
            ) from e
