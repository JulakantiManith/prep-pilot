"""Confidence analysis service for computing confidence scores from speech patterns.

Analyzes speech delivery indicators to produce a confidence score reflecting
the speaker's perceived confidence level based on hesitation patterns, pause
frequency, speech flow consistency, and response completeness.

Requirements: 9.1, 9.2
"""

from app.models.answer import ConfidenceResult

# Weight factors for confidence score computation
_HESITATION_WEIGHT = 0.25
_PAUSE_FREQUENCY_WEIGHT = 0.10
_SPEECH_FLOW_WEIGHT = 0.35
_COMPLETENESS_WEIGHT = 0.30

# Hesitation thresholds: 0 hesitations = perfect, 10+ = worst
_HESITATION_MAX = 10

# Pause frequency thresholds: 0.0 = perfect, 1.0+ = minimum (25)
_PAUSE_FREQUENCY_MAX = 1.0
_PAUSE_FREQUENCY_FLOOR = 25.0

# High-quality answer bonus
_QUALITY_BONUS = 10

# Response completeness: expected words per second for a complete response.
# Using 1.5 words/sec accounts for deliberate, STAR-style technical answers
# that are slower but substantive. Previously 2.5 was too aggressive.
_EXPECTED_WORDS_PER_SECOND = 1.5


class ConfidenceAnalyzer:
    """Analyzes speech patterns to produce a confidence score.

    This is a pure computation service with no external dependencies.
    It takes speech pattern indicators and computes a deterministic
    confidence score between 0 and 100.
    """

    def analyze(
        self,
        transcript: str,
        hesitation_count: int,
        pause_frequency: float,
        speech_flow_score: float,
        response_completeness: float,
    ) -> ConfidenceResult:
        """Compute confidence score from speech pattern indicators.

        Args:
            transcript: The transcribed text from a speech recording.
            hesitation_count: Number of hesitations detected (>= 0).
            pause_frequency: Frequency of pauses as a ratio (>= 0).
            speech_flow_score: Speech flow consistency score (0 to 1).
            response_completeness: How complete the response was (0 to 1).

        Returns:
            ConfidenceResult containing the confidence score and input metrics.
        """
        score = self._compute_confidence_score(
            hesitation_count, pause_frequency, speech_flow_score, response_completeness
        )

        return ConfidenceResult(
            score=score,
            hesitation_count=hesitation_count,
            pause_frequency=pause_frequency,
            speech_flow_score=speech_flow_score,
            response_completeness=response_completeness,
        )

    def _compute_confidence_score(
        self,
        hesitation_count: int,
        pause_frequency: float,
        speech_flow_score: float,
        response_completeness: float,
    ) -> int:
        """Compute a confidence score from 0-100.

        The score is based on four weighted factors:
        - Hesitation count (fewer = more confident): 25% weight
        - Pause frequency (lower = more confident): 10% weight
        - Speech flow consistency (higher = more confident): 35% weight
        - Response completeness (higher = more confident): 30% weight

        A high-quality answer bonus of +10 is applied when:
        - hesitation_count == 0
        - completeness score >= 75
        - speech flow score >= 70

        Args:
            hesitation_count: Number of hesitations detected.
            pause_frequency: Frequency of pauses as a ratio.
            speech_flow_score: Speech flow consistency (0 to 1).
            response_completeness: Response completeness ratio (0 to 1).

        Returns:
            Confidence score between 0 and 100 inclusive.
        """
        hesitation_score = self._score_hesitation(hesitation_count)
        pause_score = self._score_pause_frequency(pause_frequency)
        flow_score = self._score_speech_flow(speech_flow_score)
        completeness_score = self._score_completeness(response_completeness)

        raw_score = (
            (hesitation_score * _HESITATION_WEIGHT)
            + (pause_score * _PAUSE_FREQUENCY_WEIGHT)
            + (flow_score * _SPEECH_FLOW_WEIGHT)
            + (completeness_score * _COMPLETENESS_WEIGHT)
        )

        # High-quality answer bonus
        if (
            hesitation_count == 0
            and completeness_score >= 75.0
            and flow_score >= 70.0
        ):
            raw_score += _QUALITY_BONUS

        return max(0, min(100, round(raw_score)))

    def _score_hesitation(self, hesitation_count: int) -> float:
        """Score hesitation count inversely (fewer hesitations = higher score).

        Perfect score (100) when no hesitations. Score decreases linearly,
        reaching 0 at _HESITATION_MAX or more hesitations.

        Args:
            hesitation_count: Number of hesitations detected.

        Returns:
            Score from 0 to 100.
        """
        if hesitation_count <= 0:
            return 100.0

        if hesitation_count >= _HESITATION_MAX:
            return 0.0

        return 100.0 * (1.0 - hesitation_count / _HESITATION_MAX)

    def _score_pause_frequency(self, pause_frequency: float) -> float:
        """Score pause frequency inversely (lower frequency = higher score).

        Perfect score (100) when pause frequency is 0. Score decreases
        linearly, reaching a floor of 25 at _PAUSE_FREQUENCY_MAX or higher.
        This is less aggressive than before — even high pause frequency
        still gives some credit since deliberate pauses aren't always bad.

        Args:
            pause_frequency: Frequency of pauses as a ratio.

        Returns:
            Score from 25 to 100.
        """
        if pause_frequency <= 0.0:
            return 100.0

        if pause_frequency >= _PAUSE_FREQUENCY_MAX:
            return _PAUSE_FREQUENCY_FLOOR

        # Linear decrease from 100 to 25 between 0.0 and 1.0
        return _PAUSE_FREQUENCY_FLOOR + (100.0 - _PAUSE_FREQUENCY_FLOOR) * (
            1.0 - pause_frequency / _PAUSE_FREQUENCY_MAX
        )

    def _score_speech_flow(self, speech_flow_score: float) -> float:
        """Score speech flow consistency directly (higher = better).

        The speech_flow_score is already normalized to [0, 1], so
        we simply scale it to [0, 100].

        Args:
            speech_flow_score: Speech flow consistency (0 to 1).

        Returns:
            Score from 0 to 100.
        """
        clamped = max(0.0, min(1.0, speech_flow_score))
        return clamped * 100.0

    def _score_completeness(self, response_completeness: float) -> float:
        """Score response completeness directly (higher = better).

        The response_completeness is already normalized to [0, 1], so
        we simply scale it to [0, 100].

        Args:
            response_completeness: Response completeness ratio (0 to 1).

        Returns:
            Score from 0 to 100.
        """
        clamped = max(0.0, min(1.0, response_completeness))
        return clamped * 100.0

    @staticmethod
    def compute_response_completeness(
        total_words: int, duration_seconds: float
    ) -> float:
        """Compute response completeness from word count and duration.

        Uses a lower expected-words threshold (1.5 words/sec) so that
        deliberate, STAR-style technical answers at slower speaking rates
        are not penalized. A 55-second answer with 78 words scores ~0.95
        instead of the previous ~0.56.

        Args:
            total_words: Number of words in the response.
            duration_seconds: Duration of the response in seconds.

        Returns:
            Completeness ratio clamped to [0, 1].
        """
        expected_words = max(1.0, duration_seconds * _EXPECTED_WORDS_PER_SECOND)
        return min(1.0, total_words / expected_words)
