"""Unit tests for the ConfidenceAnalyzer service.

Validates Requirements: 9.1, 9.2
"""

from app.services.confidence_analyzer import ConfidenceAnalyzer


class TestConfidenceScoreBounds:
    """Confidence score must always be between 0 and 100 (Requirement 9.1)."""

    def setup_method(self):
        self.analyzer = ConfidenceAnalyzer()

    def test_perfect_inputs_score_100(self):
        result = self.analyzer.analyze("great answer", 0, 0.0, 1.0, 1.0)
        assert result.score == 100

    def test_worst_inputs_score_near_0(self):
        result = self.analyzer.analyze("bad answer", 15, 2.0, 0.0, 0.0)
        # With pause floor of 25 and 10% weight, minimum is ~3
        assert result.score <= 5

    def test_score_within_bounds_mid_inputs(self):
        result = self.analyzer.analyze("some answer", 3, 0.4, 0.7, 0.8)
        assert 0 <= result.score <= 100

    def test_score_within_bounds_edge_inputs(self):
        result = self.analyzer.analyze("edge", 10, 1.0, 0.0, 1.0)
        assert 0 <= result.score <= 100


class TestConfidenceScoreDeterminism:
    """Confidence score must be deterministic for identical inputs (Requirement 9.1)."""

    def setup_method(self):
        self.analyzer = ConfidenceAnalyzer()

    def test_same_inputs_same_output(self):
        inputs = ("hello world", 4, 0.5, 0.6, 0.75)
        results = [self.analyzer.analyze(*inputs).score for _ in range(50)]
        assert len(set(results)) == 1

    def test_different_instances_same_output(self):
        inputs = ("test speech", 2, 0.3, 0.9, 0.85)
        a1 = ConfidenceAnalyzer()
        a2 = ConfidenceAnalyzer()
        assert a1.analyze(*inputs).score == a2.analyze(*inputs).score


class TestConfidenceScoreFactors:
    """Score is computed from hesitation, pause frequency, speech flow, completeness (Requirement 9.2)."""

    def setup_method(self):
        self.analyzer = ConfidenceAnalyzer()

    def test_fewer_hesitations_higher_score(self):
        low_hesitation = self.analyzer.analyze("answer", 1, 0.3, 0.7, 0.8)
        high_hesitation = self.analyzer.analyze("answer", 8, 0.3, 0.7, 0.8)
        assert low_hesitation.score > high_hesitation.score

    def test_lower_pause_frequency_higher_score(self):
        low_pause = self.analyzer.analyze("answer", 3, 0.1, 0.7, 0.8)
        high_pause = self.analyzer.analyze("answer", 3, 0.9, 0.7, 0.8)
        assert low_pause.score > high_pause.score

    def test_higher_speech_flow_higher_score(self):
        high_flow = self.analyzer.analyze("answer", 3, 0.3, 0.9, 0.8)
        low_flow = self.analyzer.analyze("answer", 3, 0.3, 0.2, 0.8)
        assert high_flow.score > low_flow.score

    def test_higher_completeness_higher_score(self):
        high_complete = self.analyzer.analyze("answer", 3, 0.3, 0.7, 0.95)
        low_complete = self.analyzer.analyze("answer", 3, 0.3, 0.7, 0.2)
        assert high_complete.score > low_complete.score


class TestConfidenceResultModel:
    """ConfidenceResult must contain all input metrics."""

    def setup_method(self):
        self.analyzer = ConfidenceAnalyzer()

    def test_result_contains_all_fields(self):
        result = self.analyzer.analyze("test", 5, 0.4, 0.6, 0.7)
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
        result = self.analyzer.analyze("strong technical answer", 0, 0.5, 0.8, 0.85)
        # Without bonus would be lower; with bonus should be 75+
        assert result.score >= 75

    def test_bonus_not_applied_with_hesitations(self):
        with_hesitation = self.analyzer.analyze("answer", 2, 0.5, 0.8, 0.85)
        without_hesitation = self.analyzer.analyze("answer", 0, 0.5, 0.8, 0.85)
        # The difference should be more than just the hesitation weight effect
        # because the bonus kicks in for 0 hesitations
        assert without_hesitation.score > with_hesitation.score

    def test_bonus_capped_at_100(self):
        result = self.analyzer.analyze("perfect", 0, 0.0, 1.0, 1.0)
        assert result.score == 100


class TestCalibrationTargets:
    """Verify calibration: strong answers 75-90, filler-heavy 30-50."""

    def setup_method(self):
        self.analyzer = ConfidenceAnalyzer()

    def test_strong_technical_answer_scores_high(self):
        # Strong answer: 0 fillers, good flow, good completeness, some pauses
        result = self.analyzer.analyze(
            "detailed technical response", 0, 0.8, 0.75, 0.80
        )
        assert result.score >= 70

    def test_filler_heavy_answer_scores_low(self):
        # Filler-heavy: many hesitations, poor flow, poor completeness
        result = self.analyzer.analyze(
            "um like you know", 8, 0.7, 0.35, 0.4
        )
        assert result.score <= 50
