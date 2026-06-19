"""Groq Speech-to-Text client for audio transcription.

Provides a resilient interface to Groq's Whisper-based Speech-to-Text API
for converting audio recordings to text. Implements 1 retry with exponential
backoff and a 30-second timeout per request.

Returns word-level timestamps for hesitation/pause detection.

Requirements: 4.3 (transcription within 30 seconds), 17.3 (retry once on failure)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from groq import AsyncGroq, APIError, APITimeoutError, RateLimitError, AuthenticationError

from app.config import get_settings

logger = logging.getLogger(__name__)

# Timeout for each Groq API call (seconds) - Requirement 4.3
REQUEST_TIMEOUT = 30.0

# Retry configuration - Requirement 17.3
MAX_RETRIES = 1
BASE_BACKOFF_SECONDS = 2.0

# Groq speech-to-text model
GROQ_STT_MODEL = "whisper-large-v3-turbo"


@dataclass
class WordTimestamp:
    """A single word with its start and end time."""

    word: str
    start: float
    end: float


@dataclass
class TranscriptionResult:
    """Result of transcription including text and word timestamps.

    Attributes:
        text: The main transcript as returned by Whisper (may be polished).
        words: Individual word timestamps from word-level granularity.
        duration: Total audio duration in seconds.
        words_transcript: Transcript reconstructed from word-level timestamps.
            May contain filler words that the main .text has removed.
            Use this for filler-word analysis and raw speech evaluation.
    """

    text: str
    words: list[WordTimestamp] = field(default_factory=list)
    duration: float = 0.0
    words_transcript: str = ""  # Reconstructed from word timestamps


class GroqClientError(Exception):
    """Raised when Groq API call fails after all retries."""

    def __init__(self, message: str, is_retryable: bool = True) -> None:
        super().__init__(message)
        self.is_retryable = is_retryable


class GroqClient:
    """Client for Groq Speech-to-Text API with retry and timeout logic.

    Returns word-level timestamps for hesitation/pause detection.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.groq_api_key
        self._client: Optional[AsyncGroq] = None

    def _get_client(self) -> AsyncGroq:
        if self._client is None:
            if not self._api_key:
                raise GroqClientError(
                    "Groq API key is not configured. Set GROQ_API_KEY in environment.",
                    is_retryable=False,
                )
            self._client = AsyncGroq(
                api_key=self._api_key,
                timeout=REQUEST_TIMEOUT,
            )
        return self._client

    async def transcribe(
        self,
        audio_data: bytes,
        filename: str = "audio.webm",
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio data to text with word-level timestamps.

        Args:
            audio_data: Raw audio bytes to transcribe.
            filename: Filename hint for the audio format.
            language: Optional language code.

        Returns:
            TranscriptionResult with text and word timestamps.

        Raises:
            GroqClientError: If transcription fails after all retries.
        """
        if not audio_data:
            raise GroqClientError(
                "No audio data provided for transcription",
                is_retryable=False,
            )

        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                result = await self._call_groq(audio_data, filename, language)
                return result
            except GroqClientError as e:
                last_error = e
                if not e.is_retryable:
                    logger.error("Groq API non-retryable error: %s", str(e))
                    raise
                if attempt < MAX_RETRIES:
                    backoff = BASE_BACKOFF_SECONDS * (2**attempt)
                    logger.warning(
                        "Groq API call failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        MAX_RETRIES + 1,
                        backoff,
                        str(e),
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        "Groq API call failed after %d attempts: %s",
                        MAX_RETRIES + 1,
                        str(e),
                    )
            except asyncio.TimeoutError as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    backoff = BASE_BACKOFF_SECONDS * (2**attempt)
                    logger.warning(
                        "Groq API timed out (attempt %d/%d), retrying in %.1fs",
                        attempt + 1,
                        MAX_RETRIES + 1,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        "Groq API timed out after %d attempts",
                        MAX_RETRIES + 1,
                    )

        raise GroqClientError(
            f"Groq Speech-to-Text unavailable after {MAX_RETRIES + 1} attempts: {last_error}"
        )

    async def _call_groq(
        self,
        audio_data: bytes,
        filename: str,
        language: Optional[str],
    ) -> TranscriptionResult:
        """Make a single transcription request to Groq API."""
        client = self._get_client()

        try:
            result = await asyncio.wait_for(
                self._send_transcription_request(client, audio_data, filename, language),
                timeout=REQUEST_TIMEOUT,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning("Groq API request timed out after %.0fs", REQUEST_TIMEOUT)
            raise
        except AuthenticationError as e:
            raise GroqClientError(f"Invalid Groq API key: {e}", is_retryable=False) from e
        except RateLimitError as e:
            raise GroqClientError(f"Groq API rate limit exceeded: {e}", is_retryable=True) from e
        except APITimeoutError as e:
            raise GroqClientError(f"Groq API timeout: {e}", is_retryable=True) from e
        except APIError as e:
            status_code = getattr(e, "status_code", None)
            if status_code == 400:
                raise GroqClientError(
                    f"Invalid audio file or unsupported format: {e}", is_retryable=False
                ) from e
            raise GroqClientError(f"Groq API error: {e}", is_retryable=True) from e

    async def _send_transcription_request(
        self,
        client: AsyncGroq,
        audio_data: bytes,
        filename: str,
        language: Optional[str],
    ) -> TranscriptionResult:
        """Send transcription request with verbose_json and word timestamps.

        Note: Groq's whisper-large-v3-turbo produces polished/clean transcripts
        by design. Filler words may not appear in the output regardless of
        prompt settings. This is a model-level behavior, not application-level.
        Hesitation/filler detection relies on word-timestamp gap analysis instead.
        """
        kwargs: dict = {
            "model": GROQ_STT_MODEL,
            "file": (filename, audio_data),
            "response_format": "verbose_json",
            "timestamp_granularities": ["word", "segment"],
        }
        if language:
            kwargs["language"] = language

        response = await client.audio.transcriptions.create(**kwargs)

        # Extract word-level timestamps
        words: list[WordTimestamp] = []
        duration = 0.0

        if hasattr(response, "words") and response.words:
            for w in response.words:
                words.append(WordTimestamp(
                    word=w.word.strip() if hasattr(w, "word") else str(w.get("word", "")).strip(),
                    start=float(w.start) if hasattr(w, "start") else float(w.get("start", 0)),
                    end=float(w.end) if hasattr(w, "end") else float(w.get("end", 0)),
                ))
            if words:
                duration = words[-1].end

        # Fallback: get duration from segments
        if duration == 0.0 and hasattr(response, "segments") and response.segments:
            last_seg = response.segments[-1]
            duration = float(last_seg.end) if hasattr(last_seg, "end") else float(last_seg.get("end", 0))

        text = response.text if hasattr(response, "text") else ""
        words_transcript = " ".join(w.word for w in words) if words else ""

        return TranscriptionResult(
            text=text, words=words, duration=duration,
            words_transcript=words_transcript,
        )
