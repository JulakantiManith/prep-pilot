"""Transcription service wrapping the Groq Speech-to-Text client.

Provides a service-layer interface for audio-to-text conversion,
including word-level timestamps for hesitation/pause detection.

Includes safeguards against Whisper hallucination on silent audio:
- Filler-only transcripts are classified as empty responses
- Minimum word count threshold for meaningful content

Requirements: 4.3 (transcription within 30 seconds)
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.integrations.groq_client import GroqClient, GroqClientError, TranscriptionResult, WordTimestamp

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Raised when transcription fails."""

    pass


@dataclass
class HesitationAnalysis:
    """Analysis of hesitations detected from word timing gaps."""

    hesitation_count: int = 0
    total_pause_duration: float = 0.0
    avg_pause_duration: float = 0.0
    long_pauses: list[float] = field(default_factory=list)  # Pauses > threshold


# Threshold for a gap between words to count as a hesitation/filler pause
HESITATION_PAUSE_THRESHOLD = 0.4  # seconds

# Known filler words that Whisper hallucinates from silence/background noise.
# If the entire transcript consists ONLY of these words, it's treated as empty.
FILLER_ONLY_WORDS = {
    "so", "uh", "um", "ah", "oh", "eh", "hm", "hmm", "mm", "mhm",
    "like", "yeah", "yes", "no", "ok", "okay", "well", "right",
    "you know", "i mean", "basically", "actually",
}

# Minimum number of non-filler words required for a transcript to be
# considered a meaningful response (not hallucinated from silence).
MIN_MEANINGFUL_WORDS = 2


class TranscriptionService:
    """Service for converting audio recordings to text with timing data.

    Returns transcription text plus word timestamps and hesitation analysis.
    """

    def __init__(self, groq_client: Optional[GroqClient] = None) -> None:
        self._client = groq_client or GroqClient()

    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.webm",
        language: Optional[str] = None,
    ) -> str:
        """Transcribe audio data to text (simple interface for backward compat).

        Args:
            audio_data: Raw audio bytes from recording.
            filename: Filename hint for audio format detection.
            language: Optional language code.

        Returns:
            Transcribed text string.

        Raises:
            TranscriptionError: If transcription fails after retries.
        """
        result = await self.transcribe_audio_detailed(audio_data, filename, language)
        return result.text

    async def transcribe_audio_detailed(
        self,
        audio_data: bytes,
        filename: str = "audio.webm",
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio with full word timestamps.

        Args:
            audio_data: Raw audio bytes from recording.
            filename: Filename hint for audio format detection.
            language: Optional language code.

        Returns:
            TranscriptionResult with text, word timestamps, and duration.

        Raises:
            TranscriptionError: If transcription fails after retries.
        """
        if not audio_data:
            raise TranscriptionError("No audio data provided")

        logger.info(
            "Starting transcription: file=%s, size=%d bytes",
            filename,
            len(audio_data),
        )

        try:
            result = await self._client.transcribe(
                audio_data=audio_data,
                filename=filename,
                language=language,
            )
            logger.info(
                "Transcription completed: %d characters, %d words, %.1fs duration, %d word timestamps",
                len(result.text),
                len(result.text.split()),
                result.duration,
                len(result.words),
            )
            return result
        except GroqClientError as e:
            logger.error("Transcription failed: %s", str(e))
            raise TranscriptionError(f"Failed to transcribe audio: {e}") from e

    def is_meaningful_transcript(self, text: str) -> bool:
        """Check if a transcript contains meaningful speech content.

        Detects cases where the Whisper model hallucinates filler words
        from silence or background noise. A transcript is considered
        NOT meaningful if it consists entirely of common filler words
        or has fewer than MIN_MEANINGFUL_WORDS non-filler words.

        This is a known behavior of Whisper-based models: when given
        silent or near-silent audio, they may produce short filler
        outputs like "So", "Uh", "Um" rather than returning empty text.

        Args:
            text: The transcript text to evaluate.

        Returns:
            True if the transcript contains meaningful speech content,
            False if it appears to be hallucinated from silence.
        """
        if not text or not text.strip():
            return False

        # Normalize: lowercase, strip punctuation
        cleaned = text.strip().lower()
        # Remove common punctuation that Whisper adds
        for char in ".,!?;:\"'()-":
            cleaned = cleaned.replace(char, "")
        cleaned = cleaned.strip()

        if not cleaned:
            return False

        # Check if the entire transcript is a single filler word/phrase
        if cleaned in FILLER_ONLY_WORDS:
            logger.info(
                "Transcript classified as filler-only (hallucination): '%s'",
                text.strip(),
            )
            return False

        # Count non-filler words
        words = cleaned.split()
        non_filler_words = [w for w in words if w not in FILLER_ONLY_WORDS]

        if len(non_filler_words) < MIN_MEANINGFUL_WORDS:
            logger.info(
                "Transcript below meaningful threshold (%d non-filler words): '%s'",
                len(non_filler_words),
                text.strip(),
            )
            return False

        return True

    def count_filler_words_in_timestamps(
        self, words: list[WordTimestamp]
    ) -> int:
        """Count filler words found in word-level timestamp data.

        Whisper sometimes preserves filler words (um, uh, like, so) in the
        word-level timestamps even when the main .text output is cleaned.
        This provides a secondary source of filler detection.

        Args:
            words: List of word timestamps from transcription.

        Returns:
            Count of filler words found in the word timestamps.
        """
        if not words:
            return 0

        filler_count = 0
        for w in words:
            word_lower = w.word.strip().lower().rstrip(".,!?;:")
            if word_lower in FILLER_ONLY_WORDS:
                filler_count += 1
        return filler_count

    def analyze_hesitations(
        self,
        words: list[WordTimestamp],
        threshold: float = HESITATION_PAUSE_THRESHOLD,
    ) -> HesitationAnalysis:
        """Detect hesitations from gaps between word timestamps.

        A gap > threshold between consecutive words indicates a hesitation
        point where a filler word (um, uh) likely occurred but was stripped
        by the transcription model.

        Args:
            words: List of word timestamps from transcription.
            threshold: Minimum gap in seconds to count as hesitation.

        Returns:
            HesitationAnalysis with count and timing details.
        """
        if len(words) < 2:
            return HesitationAnalysis()

        hesitation_count = 0
        total_pause_duration = 0.0
        long_pauses: list[float] = []

        for i in range(1, len(words)):
            gap = words[i].start - words[i - 1].end
            if gap >= threshold:
                hesitation_count += 1
                total_pause_duration += gap
                long_pauses.append(gap)

        avg_pause = total_pause_duration / hesitation_count if hesitation_count > 0 else 0.0

        return HesitationAnalysis(
            hesitation_count=hesitation_count,
            total_pause_duration=total_pause_duration,
            avg_pause_duration=avg_pause,
            long_pauses=long_pauses,
        )
