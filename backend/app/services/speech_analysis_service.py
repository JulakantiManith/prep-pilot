"""Speech analysis service for computing delivery metrics from transcripts.

Analyzes transcribed speech to produce metrics including words per minute,
filler word detection, communication scoring, and pause estimation.

Requirements: 4.4, 8.1, 8.2, 8.3, 8.4, 8.5
"""

import re

from app.models.answer import SpeechMetrics

# Filler words to detect in transcripts
_SINGLE_FILLER_WORDS = {"um", "uh", "like", "actually", "basically", "so"}
_MULTI_FILLER_PHRASES = ["you know"]

# Ideal WPM range for communication scoring
_WPM_IDEAL_LOW = 120
_WPM_IDEAL_HIGH = 160

# Average speaking rate used for pause estimation (words per second)
_AVG_SPEAKING_RATE_WPS = 2.5

# Minimum content thresholds for meaningful analysis
_MIN_WORDS_FOR_VALID_RESPONSE = 5
_MIN_WORDS_FOR_SUBSTANTIVE_RESPONSE = 15


class SpeechAnalysisService:
    """Analyzes transcripts to produce speech delivery metrics.

    This is a pure computation service with no external dependencies.
    It takes a transcript and duration, then computes WPM, detects
    filler words, estimates pause patterns, and produces a communication
    score.
    """

    def analyze(self, transcript: str, duration_seconds: float) -> SpeechMetrics:
        """Compute speech metrics from a transcript and its duration.

        Args:
            transcript: The transcribed text from a speech recording.
            duration_seconds: Total duration of the recording in seconds.

        Returns:
            SpeechMetrics containing WPM, filler word counts,
            communication score, and other delivery metrics.
        """
        words = self._tokenize(transcript)
        total_words = len(words)

        # WPM calculation (Requirement 8.1)
        wpm = round(total_words / (duration_seconds / 60)) if duration_seconds > 0 else 0

        # Filler word detection (Requirement 8.2)
        filler_words_detail = self._detect_filler_words(transcript, words)
        filler_word_count = sum(filler_words_detail.values())

        # Pause estimation (Requirement 8.4)
        avg_pause_duration = self._estimate_avg_pause_duration(
            total_words, duration_seconds
        )

        # Communication score (Requirement 8.3)
        communication_score = self._compute_communication_score(
            wpm, filler_word_count, total_words, avg_pause_duration
        )

        # WPM range flag (Requirement 8.5)
        wpm_in_range = _WPM_IDEAL_LOW <= wpm <= _WPM_IDEAL_HIGH

        return SpeechMetrics(
            wpm=wpm,
            total_words=total_words,
            filler_word_count=filler_word_count,
            filler_words_detail=filler_words_detail,
            speaking_duration=duration_seconds,
            avg_pause_duration=avg_pause_duration,
            communication_score=communication_score,
            wpm_in_range=wpm_in_range,
        )

    def _tokenize(self, transcript: str) -> list[str]:
        """Split transcript into individual word tokens.

        Uses regex to extract word sequences, normalizing to lowercase.

        Args:
            transcript: Raw transcript text.

        Returns:
            List of lowercase word tokens.
        """
        return re.findall(r"[a-zA-Z']+", transcript.lower())

    def _detect_filler_words(
        self, transcript: str, words: list[str]
    ) -> dict[str, int]:
        """Detect and count filler words in the transcript.

        Handles both single-word fillers (um, uh, like, actually, basically)
        and multi-word phrases (you know).

        Args:
            transcript: Original transcript text.
            words: Pre-tokenized word list (lowercase).

        Returns:
            Dictionary mapping filler word/phrase to occurrence count.
        """
        detail: dict[str, int] = {}

        # Count single-word fillers
        for word in words:
            if word in _SINGLE_FILLER_WORDS:
                detail[word] = detail.get(word, 0) + 1

        # Count multi-word filler phrases
        transcript_lower = transcript.lower()
        for phrase in _MULTI_FILLER_PHRASES:
            count = self._count_phrase_occurrences(transcript_lower, phrase)
            if count > 0:
                detail[phrase] = count

        return detail

    def _count_phrase_occurrences(self, text: str, phrase: str) -> int:
        """Count non-overlapping occurrences of a phrase using word boundaries.

        Args:
            text: Lowercase text to search in.
            phrase: Phrase to search for.

        Returns:
            Number of occurrences found.
        """
        pattern = r"\b" + re.escape(phrase) + r"\b"
        return len(re.findall(pattern, text))

    def _estimate_avg_pause_duration(
        self, total_words: int, duration_seconds: float
    ) -> float:
        """Estimate average pause duration from word count and total duration.

        Since we only have the transcript and total duration, we estimate
        speaking time based on an average speaking rate, then derive pause
        time from the remainder.

        Args:
            total_words: Number of words in the transcript.
            duration_seconds: Total recording duration in seconds.

        Returns:
            Estimated average pause duration in seconds (non-negative).
        """
        estimated_speaking_time = total_words / _AVG_SPEAKING_RATE_WPS
        pause_time = max(0.0, duration_seconds - estimated_speaking_time)

        # Estimate number of pauses as roughly one pause per sentence/clause
        # Approximate by number of words divided by average clause length (~8 words)
        estimated_pause_count = max(1, total_words // 8)

        avg_pause = pause_time / estimated_pause_count
        return round(avg_pause, 3)

    def _compute_communication_score(
        self,
        wpm: int,
        filler_word_count: int,
        total_words: int,
        avg_pause_duration: float,
    ) -> int:
        """Compute a communication score from 0-100.

        The score is based on three weighted factors:
        - WPM proximity to the ideal range (120-160): 40% weight
        - Filler word frequency relative to total words: 35% weight
        - Pause pattern (shorter avg pauses are better): 25% weight

        Safeguards:
        - Empty or near-empty responses (< 5 words) receive score 0-5.
        - Responses that are entirely filler words receive score 0-10.
        - Short responses (< 15 words) are capped at 30.

        Args:
            wpm: Words per minute.
            filler_word_count: Total number of filler words detected.
            total_words: Total word count in transcript.
            avg_pause_duration: Estimated average pause duration in seconds.

        Returns:
            Communication score between 0 and 100 inclusive.
        """
        # Safeguard: empty or near-empty responses cannot score well
        if total_words < _MIN_WORDS_FOR_VALID_RESPONSE:
            # 0-4 words: essentially silence or a single utterance
            return min(5, total_words)

        # Safeguard: filler-only responses
        non_filler_words = total_words - filler_word_count
        if non_filler_words <= 0:
            # Every word is a filler — this is not a meaningful response
            return 0
        if non_filler_words < _MIN_WORDS_FOR_VALID_RESPONSE:
            # Almost all filler with minimal content
            return min(10, non_filler_words * 2)

        # WPM component (40% weight)
        wpm_score = self._score_wpm(wpm)

        # Filler word component (35% weight)
        filler_score = self._score_filler_frequency(filler_word_count, total_words)

        # Pause component (25% weight)
        pause_score = self._score_pause_duration(avg_pause_duration)

        # Weighted combination
        raw_score = (wpm_score * 0.40) + (filler_score * 0.35) + (pause_score * 0.25)

        # Safeguard: short responses (< 15 substantive words) are capped
        if total_words < _MIN_WORDS_FOR_SUBSTANTIVE_RESPONSE:
            raw_score = min(raw_score, 30.0)

        return max(0, min(100, round(raw_score)))

    def _score_wpm(self, wpm: int) -> float:
        """Score WPM based on proximity to ideal range (120-160).

        Perfect score (100) when within the ideal range.
        Score decreases linearly as WPM moves away from the range.

        Args:
            wpm: Words per minute value.

        Returns:
            Score from 0 to 100.
        """
        if _WPM_IDEAL_LOW <= wpm <= _WPM_IDEAL_HIGH:
            return 100.0

        # Distance from the nearest boundary of ideal range
        if wpm < _WPM_IDEAL_LOW:
            distance = _WPM_IDEAL_LOW - wpm
        else:
            distance = wpm - _WPM_IDEAL_HIGH

        # Lose ~1 point per WPM away from ideal, capped at 0
        penalty = distance * 1.0
        return max(0.0, 100.0 - penalty)

    def _score_filler_frequency(
        self, filler_word_count: int, total_words: int
    ) -> float:
        """Score filler word usage based on frequency.

        Perfect score (100) when no fillers AND sufficient content.
        Score decreases as the filler-to-word ratio increases.
        Returns 0 when there are no words (empty response).

        Args:
            filler_word_count: Number of filler words detected.
            total_words: Total word count.

        Returns:
            Score from 0 to 100.
        """
        if total_words == 0:
            # Empty transcript — no content to evaluate, not a "good" score
            return 0.0

        if filler_word_count == 0:
            return 100.0

        filler_ratio = filler_word_count / total_words
        # A ratio of 0.10 (10% filler words) or higher results in score of 0
        penalty = (filler_ratio / 0.10) * 100.0
        return max(0.0, 100.0 - penalty)

    def _score_pause_duration(self, avg_pause_duration: float) -> float:
        """Score pause patterns based on average pause duration.

        Short pauses (< 0.5s) are ideal. Score decreases as avg pause
        duration increases, with pauses > 3s scoring 0.

        Args:
            avg_pause_duration: Average pause duration in seconds.

        Returns:
            Score from 0 to 100.
        """
        if avg_pause_duration <= 0.5:
            return 100.0

        if avg_pause_duration >= 3.0:
            return 0.0

        # Linear decrease from 100 to 0 between 0.5s and 3.0s
        return max(0.0, 100.0 - ((avg_pause_duration - 0.5) / 2.5) * 100.0)
