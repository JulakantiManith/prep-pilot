"""Unit tests for the ConfidenceAnalyzer service.

Validates Requirements: 9.1, 9.2
"""

from app.services.confidence_analyzer import ConfidenceAnalyzer

# Realistic transcripts with sufficient word count for meaningful analysis
_GOOD_TRANSCRIPT = (
    "I have extensive experience building distributed systems using microservices "
    "architecture and have led multiple cross-functional teams to deliver projects on time"
)
_MID_TRANSCRIPT = (
    "I worked on several projects involving backend development and I enjoyed "
    "collaborating with my team members on various tasks throughout the year"
)
_WEAK_TRANSCRIPT = (
    "Um like you know I basically worked on some stuff and it was actually "
    "interesting to learn about different technologies in the process overall"
)
_SHORT_BUT_VALID = "I have worked on distributed systems and microservices before"
_STRONG_TECHNICAL = (
    "In my previous role I implemented a caching layer using Redis which reduced "
    "latency by forty percent and improved throughput significantly across all services"
)


class TestConfidenceScoreBounds:
    """Confidence score must always be between 0 and 100 (Requirement 9.1)."""

    def setup_method(self):
        self.analyzer = ConfidenceAnalyzer()

    def test_perfect_inputs_score_100(self):
        result = self.analyzer.analyze(_GOOD_TRANSCRIPT, 0, 0.0, 1.0, 1.0)
        assert result.score == 100

    def test_worst_inputs_score_near_0(self):
        result = self.analyzer.analyze(_MID_TRANSCRIPT, 15, 2.0, 0.0, 0.0)
        # With pause floor of 25 and 10% weight, minimum is ~3
        assert result.score <= 5

    def test_score_within_bounds_mid_inputs(self):
        result = self.analyzer.analyze(_MID_TRANSCRIPT, 3, 0.4, 0.7, 0.8)
        assert 0 <= result.score <= 100

    def test_score_within_bounds_edge_inputs(self):
        result = self.analyzer.analyze(_MID_TRANSCRIPT, 10, 1.0, 0.0, 1.0)
        assert 0 <= result.score <= 100


class TestConfidenceScoreDeterminism:
    """Confidence score must be deterministic for identical inputs (Requirement 9.1)."""

    def setup_method(self):
        self.analyzer = ConfidenceAnalyzer()

    def test_same_inputs_same_output(self):
        inputs = (_MID_TRANSCRIPT, 4, 0.5, 0.6, 0.75)
        results = [self.analyzer.analyze(*inputs).score for _ in range(50)]
        assert len(set(results)) == 1

    def test_different_instances_same_output(self):
        inputs = (_GOOD_TRANSCRIPT, 2, 0.3, 0.9, 0.85)
        a1 = ConfidenceAnalyzer()
        a2 = ConfidenceAnalyzer()
        assert a1.analyze(*inputs).score == a2.analyze(*inputs).score


class TestConfidenceScoreFactors:
    """Score is computed from hesitation, pause frequency, speech flow, completeness (Requirement 9.2)."""

    def setup_method(self):
        self.analyzer = ConfidenceAnalyzer()

    def test_fewer_hesitations_higher_score(self):
        low_hesitation = self.analyzer.analyze(_MID_TRANSCRIPT, 1, 0.3, 0.7, 0.8)
        high_hesitation = self.analyzer.analyze(_MID_TRANSCRIPT, 8, 0.3, 0.7, 0.8)
        assert low_hesitation.score > high_hesitation.score

    def test_lower_pause_frequency_higher_score(self):
        low_pause = self.analyzer.analyze(_MID_TRANSCRIPT, 3, 0.1, 0.7, 0.8)
        high_pause = self.analyzer.analyze(_MID_TRANSCRIPT, 3, 0.9, 0.7, 0.8)
        assert low_pause.score > high_pause.score

    def test_higher_speech_flow_higher_score(self):
        high_flow = self.analyzer.analyze(_MID_TRANSCRIPT, 3, 0.3, 0.9, 0.8)
        low_flow = self.analyzer.analyze(_MID_TRANSCRIPT, 3, 0.3, 0.2, 0.8)
        assert high_flow.score > low_flow.score

    def test_higher_completeness_higher_score(self):
        high_complete = self.analyzer.analyze(_MID_TRANSCRIPT, 3, 0.3, 0.7, 0.95)
        low_complete = self.analyzer.analyze(_MID_TRANSCRIPT, 3, 0.3, 0.7, 0.2)
        assert high_complete.score > low_complete.score


class TestConfidenceResultModel:
    """ConfidenceResult must contain all input metrics."""

    def setup_method(self):
        self.analyzer = ConfidenceAnalyzer()

    def test_result_contains_all_fields(self):
        result = self.analyzer.analyze(_MID_TRANSCRIPT, 5, 0.4, 0.6, 0.7)
        assert result.hesitation_count == 5
        assert result.pause_frequency == 0.4
        assert result.speech_flow_score == 0.6
        assert result.response_completeness == 0.7
        assert isinstance(result.score, int)


class TestHighQualityBonus:
    """High-quality answers with no hesitation get a +10 bonus."""

    def setup_method(self):
        self.analyzer = ConfidenceAnalyzer()

    def test_bonus_applied_for_strong_answer(self):
        # 0 hesitations, high flow (0.8 -> 80), high completeness (0.85 -> 85)
        result = self.analyzer.analyze(_STRONG_TECHNICAL, 0, 0.5, 0.8, 0.85)
        # Without bonus would be lower; with bonus should be 75+
        assert result.score >= 75

    def test_bonus_not_applied_with_hesitations(self):
        with_hesitation = self.analyzer.analyze(_MID_TRANSCRIPT, 2, 0.5, 0.8, 0.85)
        without_hesitation = self.analyzer.analyze(_MID_TRANSCRIPT, 0, 0.5, 0.8, 0.85)
        # The difference should be more than just the hesitation weight effect
        # because the bonus kicks in for 0 hesitations
        assert without_hesitation.score > with_hesitation.score

    def test_bonus_capped_at_100(self):
        result = self.analyzer.analyze(_GOOD_TRANSCRIPT, 0, 0.0, 1.0, 1.0)
        assert result.score == 100


class TestCalibrationTargets:
    """Verify calibration: strong answers 75-90, filler-heavy 30-50."""

    def setup_method(self):
        self.analyzer = ConfidenceAnalyzer()

    def test_strong_technical_answer_scores_high(self):
        # Strong answer: 0 fillers, good flow, good completeness, some pauses
        result = self.analyzer.analyze(
            _STRONG_TECHNICAL, 0, 0.8, 0.75, 0.80
        )
        assert result.score >= 70

    def test_filler_heavy_answer_scores_low(self):
        # Filler-heavy: many hesitations, poor flow, poor completeness
        result = self.analyzer.analyze(
            _WEAK_TRANSCRIPT, 8, 0.7, 0.35, 0.4
        )
        assert result.score <= 50


class TestMinimumContentSafeguards:
    """Verify that empty, filler-only, and very short responses get low scores."""

    def setup_method(self):
        self.analyzer = ConfidenceAnalyzer()

    def test_empty_transcript_scores_zero(self):
        result = self.analyzer.analyze("", 0, 0.0, 1.0, 1.0)
        assert result.score == 0

    def test_single_word_scores_very_low(self):
        result = self.analyzer.analyze("So", 0, 0.0, 1.0, 1.0)
        assert result.score <= 5

    def test_filler_only_scores_very_low(self):
        result = self.analyzer.analyze("um uh like basically", 5, 0.8, 0.2, 0.1)
        assert result.score <= 10

    def test_few_words_capped(self):
        # 6 words, meets minimum but not substantive threshold
        result = self.analyzer.analyze(
            "I worked on some projects before recently", 0, 0.0, 1.0, 1.0
        )
        assert result.score <= 25

    def test_substantive_response_not_capped(self):
        result = self.analyzer.analyze(_GOOD_TRANSCRIPT, 0, 0.0, 1.0, 1.0)
        assert result.score >= 90
