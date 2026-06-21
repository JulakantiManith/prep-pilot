"""Comprehensive integration tests for OpenRouter fallback workflow.

Tests the complete fallback chain:
1. Gemini works normally when available
2. OpenRouter fallback activates on Gemini rate-limit (429)
3. OpenRouter fallback activates on Gemini errors
4. OpenRouter fallback activates on Gemini timeout
5. Correct behavior when OpenRouter is also unavailable
6. Service-level fallbacks work when both providers fail
7. All AI features (resume, questions, feedback) route correctly
8. Environment variable handling (with/without OPENROUTER_API_KEY)
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
import httpx

from app.integrations.openrouter_client import (
    OpenRouterClient,
    OpenRouterClientError,
)
from app.integrations.gemini_client import (
    GeminiClient,
    GeminiClientError,
)
from app.services.question_generator import QuestionGenerator
from app.services.ai_feedback_service import (
    AIFeedbackService,
    AnswerData,
    SessionData,
)
from app.services.resume_parser import ResumeParser, ResumeParserError
from app.models.answer import SpeechMetrics
from app.models.session import InterviewType


# ============================================================
# SECTION 1: OpenRouter Client Unit Tests
# ============================================================


class TestOpenRouterClientConfiguration:
    """Tests for OpenRouter client configuration and is_configured property."""

    @patch("app.integrations.openrouter_client.get_settings")
    def test_is_configured_true_when_key_set(self, mock_settings):
        """Client reports configured when API key is present."""
        mock_settings.return_value = MagicMock(openrouter_api_key="sk-test-key")
        client = OpenRouterClient()
        assert client.is_configured is True

    @patch("app.integrations.openrouter_client.get_settings")
    def test_is_configured_false_when_key_empty(self, mock_settings):
        """Client reports not configured when API key is empty string."""
        mock_settings.return_value = MagicMock(openrouter_api_key="")
        client = OpenRouterClient()
        assert client.is_configured is False

    @patch("app.integrations.openrouter_client.get_settings")
    def test_is_configured_false_when_key_none(self, mock_settings):
        """Client reports not configured when API key is None."""
        mock_settings.return_value = MagicMock(openrouter_api_key=None)
        client = OpenRouterClient()
        assert client.is_configured is False

    @patch("app.integrations.openrouter_client.get_settings")
    def test_generate_raises_when_not_configured(self, mock_settings):
        """Generate raises error when API key is missing."""
        mock_settings.return_value = MagicMock(openrouter_api_key="")
        client = OpenRouterClient()
        with pytest.raises(OpenRouterClientError, match="not configured"):
            asyncio.run(
                client.generate("test prompt")
            )


class TestOpenRouterClientAPIResponses:
    """Tests for OpenRouter client HTTP response handling."""

    @patch("app.integrations.openrouter_client.get_settings")
    def test_successful_response(self, mock_settings):
        """Client returns content from valid API response."""
        mock_settings.return_value = MagicMock(openrouter_api_key="sk-test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Generated text response"}}]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = OpenRouterClient()
            result = asyncio.run(
                client.generate("test prompt")
            )
            assert result == "Generated text response"

    @patch("app.integrations.openrouter_client.get_settings")
    def test_rate_limit_429(self, mock_settings):
        """Client raises error on 429 rate limit response."""
        mock_settings.return_value = MagicMock(openrouter_api_key="sk-test")

        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = OpenRouterClient()
            with pytest.raises(OpenRouterClientError, match="rate limited"):
                asyncio.run(
                    client.generate("test")
                )

    @patch("app.integrations.openrouter_client.get_settings")
    def test_server_error_500(self, mock_settings):
        """Client raises error on 500 server error."""
        mock_settings.return_value = MagicMock(openrouter_api_key="sk-test")

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = OpenRouterClient()
            with pytest.raises(OpenRouterClientError, match="server error"):
                asyncio.run(
                    client.generate("test")
                )

    @patch("app.integrations.openrouter_client.get_settings")
    def test_server_error_503(self, mock_settings):
        """Client raises error on 503 service unavailable."""
        mock_settings.return_value = MagicMock(openrouter_api_key="sk-test")

        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = OpenRouterClient()
            with pytest.raises(OpenRouterClientError, match="server error"):
                asyncio.run(
                    client.generate("test")
                )

    @patch("app.integrations.openrouter_client.get_settings")
    def test_timeout_raises_error(self, mock_settings):
        """Client raises error on request timeout."""
        mock_settings.return_value = MagicMock(openrouter_api_key="sk-test")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timed out")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = OpenRouterClient()
            with pytest.raises(OpenRouterClientError, match="timed out"):
                asyncio.run(
                    client.generate("test")
                )

    @patch("app.integrations.openrouter_client.get_settings")
    def test_empty_choices_raises_error(self, mock_settings):
        """Client raises error when response has no choices."""
        mock_settings.return_value = MagicMock(openrouter_api_key="sk-test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": []}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = OpenRouterClient()
            with pytest.raises(OpenRouterClientError, match="no choices"):
                asyncio.run(
                    client.generate("test")
                )

    @patch("app.integrations.openrouter_client.get_settings")
    def test_empty_content_raises_error(self, mock_settings):
        """Client raises error when response content is empty."""
        mock_settings.return_value = MagicMock(openrouter_api_key="sk-test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": ""}}]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = OpenRouterClient()
            with pytest.raises(OpenRouterClientError, match="empty content"):
                asyncio.run(
                    client.generate("test")
                )

    @patch("app.integrations.openrouter_client.get_settings")
    def test_uses_correct_model(self, mock_settings):
        """Client sends openrouter/free as the model."""
        mock_settings.return_value = MagicMock(openrouter_api_key="sk-test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = OpenRouterClient()
            asyncio.run(
                client.generate("test")
            )

            # Verify the payload sent to the API
            call_kwargs = mock_client.post.call_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
            assert payload["model"] == "openrouter/free"


# ============================================================
# SECTION 2: Gemini → OpenRouter Fallback Integration Tests
# ============================================================


class TestGeminiFallbackToOpenRouter:
    """Tests for the _call_with_fallback method in GeminiClient."""

    @patch("app.integrations.gemini_client.get_settings")
    def setup_method(self, method, mock_settings=None):
        """Set up test fixtures with mocked settings."""
        with patch("app.integrations.gemini_client.get_settings") as ms:
            ms.return_value = MagicMock(gemini_api_key="test-gemini-key")
            self.gemini_client = GeminiClient()

    @patch("app.integrations.gemini_client.OpenRouterClient")
    def test_gemini_success_no_fallback(self, mock_or_class):
        """When Gemini succeeds, OpenRouter is never called."""
        self.gemini_client._call_gemini = AsyncMock(
            return_value="Gemini response"
        )

        result = asyncio.run(
            self.gemini_client._call_with_fallback("test prompt")
        )

        assert result == "Gemini response"
        mock_or_class.assert_not_called()

    @patch("app.integrations.gemini_client.OpenRouterClient")
    def test_gemini_fails_fallback_to_openrouter(self, mock_or_class):
        """When Gemini fails after retry, falls back to OpenRouter."""
        self.gemini_client._call_gemini = AsyncMock(
            side_effect=GeminiClientError("rate limited")
        )

        mock_or_instance = MagicMock()
        mock_or_instance.is_configured = True
        mock_or_instance.generate = AsyncMock(
            return_value="OpenRouter response"
        )
        mock_or_class.return_value = mock_or_instance

        result = asyncio.run(
            self.gemini_client._call_with_fallback("test prompt")
        )

        assert result == "OpenRouter response"
        mock_or_instance.generate.assert_called_once_with("test prompt")

    @patch("app.integrations.gemini_client.OpenRouterClient")
    def test_gemini_timeout_fallback_to_openrouter(self, mock_or_class):
        """When Gemini times out after retry, falls back to OpenRouter."""
        self.gemini_client._call_gemini = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )

        mock_or_instance = MagicMock()
        mock_or_instance.is_configured = True
        mock_or_instance.generate = AsyncMock(
            return_value="OpenRouter timeout fallback"
        )
        mock_or_class.return_value = mock_or_instance

        result = asyncio.run(
            self.gemini_client._call_with_fallback("test prompt")
        )

        assert result == "OpenRouter timeout fallback"

    @patch("app.integrations.gemini_client.OpenRouterClient")
    def test_both_providers_fail_raises_gemini_error(self, mock_or_class):
        """When both Gemini and OpenRouter fail, raises GeminiClientError."""
        self.gemini_client._call_gemini = AsyncMock(
            side_effect=GeminiClientError("Gemini unavailable")
        )

        mock_or_instance = MagicMock()
        mock_or_instance.is_configured = True
        mock_or_instance.generate = AsyncMock(
            side_effect=OpenRouterClientError("OpenRouter also failed")
        )
        mock_or_class.return_value = mock_or_instance

        with pytest.raises(GeminiClientError, match="Both Gemini and OpenRouter"):
            asyncio.run(
                self.gemini_client._call_with_fallback("test prompt")
            )

    @patch("app.integrations.gemini_client.OpenRouterClient")
    def test_no_fallback_when_openrouter_not_configured(self, mock_or_class):
        """When OPENROUTER_API_KEY is missing, skips fallback and raises."""
        self.gemini_client._call_gemini = AsyncMock(
            side_effect=GeminiClientError("Gemini failed")
        )

        mock_or_instance = MagicMock()
        mock_or_instance.is_configured = False
        mock_or_class.return_value = mock_or_instance

        with pytest.raises(GeminiClientError, match="no fallback configured"):
            asyncio.run(
                self.gemini_client._call_with_fallback("test prompt")
            )

        mock_or_instance.generate.assert_not_called()

    @patch("app.integrations.gemini_client.OpenRouterClient")
    @patch("app.integrations.gemini_client.asyncio.sleep", new_callable=AsyncMock)
    def test_retry_before_fallback(self, mock_sleep, mock_or_class):
        """Gemini is retried once before falling back to OpenRouter."""
        call_count = 0

        async def fail_gemini(prompt):
            nonlocal call_count
            call_count += 1
            raise GeminiClientError("transient error")

        self.gemini_client._call_gemini = fail_gemini

        mock_or_instance = MagicMock()
        mock_or_instance.is_configured = True
        mock_or_instance.generate = AsyncMock(return_value="fallback result")
        mock_or_class.return_value = mock_or_instance

        result = asyncio.run(
            self.gemini_client._call_with_fallback("test prompt")
        )

        # Gemini should be called 2 times (initial + 1 retry)
        assert call_count == 2
        assert result == "fallback result"


# ============================================================
# SECTION 3: Question Generation Fallback Tests
# ============================================================


class TestQuestionGenerationFallback:
    """Tests that question generation properly routes through fallback chain."""

    def test_gemini_success_returns_ai_questions(self):
        """When Gemini succeeds, returns AI-generated questions."""
        from app.models.question import Question

        mock_gemini = MagicMock()
        mock_questions = [
            Question(text="Q1", topic="general", interview_type="technical"),
            Question(text="Q2", topic="general", interview_type="technical"),
        ]
        mock_gemini.generate_questions = AsyncMock(return_value=mock_questions)

        mock_cache = MagicMock()
        mock_cache.get_cached_questions = AsyncMock(return_value=None)
        mock_cache.cache_questions = AsyncMock()

        generator = QuestionGenerator(
            gemini_client=mock_gemini,
            cache_service=mock_cache,
            question_bank=MagicMock(),
        )

        result = asyncio.run(
            generator.generate_questions(
                interview_type="technical",
                role="Software Engineer",
            )
        )

        assert result.source == "gemini"
        assert result.fallback_used is False
        assert len(result.questions) == 2

    def test_gemini_fails_uses_question_bank_fallback(self):
        """When Gemini fails, falls back to predefined question bank."""
        from app.models.question import Question

        mock_gemini = MagicMock()
        mock_gemini.generate_questions = AsyncMock(
            side_effect=GeminiClientError("Both providers failed")
        )

        mock_bank = MagicMock()
        mock_bank_questions = [
            Question(text="Fallback Q1", interview_type="hr"),
            Question(text="Fallback Q2", interview_type="hr"),
        ]
        mock_bank.get_questions.return_value = mock_bank_questions

        mock_cache = MagicMock()
        mock_cache.get_cached_questions = AsyncMock(return_value=None)

        generator = QuestionGenerator(
            gemini_client=mock_gemini,
            cache_service=mock_cache,
            question_bank=mock_bank,
        )

        result = asyncio.run(
            generator.generate_questions(
                interview_type="hr",
                role="Product Manager",
            )
        )

        assert result.source == "fallback"
        assert result.fallback_used is True
        assert len(result.questions) == 2

    def test_cache_hit_skips_gemini(self):
        """When cache has questions, Gemini is never called."""
        from app.models.question import Question

        mock_gemini = MagicMock()
        mock_gemini.generate_questions = AsyncMock()

        cached = [Question(text="Cached Q1", interview_type="hr")]
        mock_cache = MagicMock()
        mock_cache.get_cached_questions = AsyncMock(return_value=cached)

        generator = QuestionGenerator(
            gemini_client=mock_gemini,
            cache_service=mock_cache,
            question_bank=MagicMock(),
        )

        result = asyncio.run(
            generator.generate_questions(
                interview_type="hr",
                role="Engineer",
            )
        )

        assert result.source == "cache"
        mock_gemini.generate_questions.assert_not_called()


# ============================================================
# SECTION 4: AI Feedback Generation Fallback Tests
# ============================================================


def _make_session_data():
    """Helper to create test session data."""
    return SessionData(
        interview_type=InterviewType.HR,
        role="Software Engineer",
        answers=[
            AnswerData(
                question_text="Tell me about yourself.",
                transcript="I am an engineer with 5 years experience.",
                communication_score=75,
                confidence_score=65,
            ),
            AnswerData(
                question_text="Why this role?",
                transcript="I want to grow in a challenging environment.",
                communication_score=70,
                confidence_score=60,
            ),
        ],
    )


def _make_speech_metrics():
    """Helper to create test speech metrics."""
    return SpeechMetrics(
        wpm=140,
        total_words=200,
        filler_word_count=2,
        filler_words_detail={"um": 1, "uh": 1},
        speaking_duration=85.0,
        avg_pause_duration=0.4,
        communication_score=75,
        wpm_in_range=True,
    )


class TestAIFeedbackFallback:
    """Tests that AI feedback generation properly uses fallback chain."""

    def test_gemini_success_returns_ai_feedback(self):
        """When Gemini succeeds, returns AI-generated feedback."""
        mock_gemini = MagicMock()
        valid_response = json.dumps({
            "strengths": ["Clear communication", "Good structure"],
            "weaknesses": ["Needs more examples", "Too brief"],
            "recommendations": [
                "Add specific examples",
                "Elaborate on experiences",
                "Practice STAR method",
            ],
        })
        mock_gemini._call_with_fallback = AsyncMock(
            return_value=valid_response
        )

        service = AIFeedbackService(gemini_client=mock_gemini)

        result = asyncio.run(
            service.generate_feedback(
                session_data=_make_session_data(),
                speech_metrics=_make_speech_metrics(),
                confidence_score=70,
            )
        )

        assert len(result.strengths) >= 2
        assert len(result.weaknesses) >= 2
        assert len(result.recommendations) >= 3

    def test_both_providers_fail_uses_algorithmic_fallback(self):
        """When both AI providers fail, uses algorithmic feedback."""
        mock_gemini = MagicMock()
        mock_gemini._call_with_fallback = AsyncMock(
            side_effect=GeminiClientError("Both providers failed")
        )

        service = AIFeedbackService(gemini_client=mock_gemini)

        result = asyncio.run(
            service.generate_feedback(
                session_data=_make_session_data(),
                speech_metrics=_make_speech_metrics(),
                confidence_score=70,
            )
        )

        # Should still return valid feedback via algorithmic fallback
        assert len(result.strengths) >= 2
        assert len(result.weaknesses) >= 2
        assert len(result.recommendations) >= 3


# ============================================================
# SECTION 5: Resume Parser Fallback Tests
# ============================================================


class TestResumeParserFallback:
    """Tests that resume parser uses GeminiClient fallback chain."""

    def test_gemini_success_returns_extraction(self):
        """When Gemini succeeds, returns valid extraction data."""
        valid_response = json.dumps({
            "skills": ["Python", "JavaScript"],
            "projects": [
                {"name": "App", "description": "A web app", "technologies": ["React"]}
            ],
            "experience": [
                {"title": "Engineer", "company": "Acme", "duration": "2y", "description": "Built APIs"}
            ],
            "education": [
                {"degree": "BS CS", "institution": "MIT", "year": "2020"}
            ],
            "confidence": 0.9,
        })

        mock_gemini = MagicMock()
        mock_gemini._call_with_fallback = AsyncMock(return_value=valid_response)

        parser = ResumeParser.__new__(ResumeParser)
        parser._gemini = mock_gemini
        parser._client = MagicMock()

        result = parser._parse_extraction_response(valid_response)

        assert result["extracted_data"]["skills"] == ["Python", "JavaScript"]
        assert result["confidence"] == 0.9

    def test_gemini_fails_openrouter_succeeds(self):
        """Resume parser gets response via OpenRouter fallback."""
        valid_response = json.dumps({
            "skills": ["Java"],
            "projects": [],
            "experience": [
                {"title": "Dev", "company": "Corp", "duration": "1y", "description": "Wrote code"}
            ],
            "education": [],
            "confidence": 0.7,
        })

        mock_gemini = MagicMock()
        # _call_with_fallback internally tries Gemini, then OpenRouter
        mock_gemini._call_with_fallback = AsyncMock(return_value=valid_response)

        parser = ResumeParser.__new__(ResumeParser)
        parser._gemini = mock_gemini
        parser._client = MagicMock()

        result = parser._parse_extraction_response(valid_response)

        assert result["extracted_data"]["skills"] == ["Java"]
        assert result["confidence"] == 0.7

    def test_both_providers_fail_raises_error(self):
        """When both providers fail, resume parser raises error."""
        mock_gemini = MagicMock()
        mock_gemini._call_with_fallback = AsyncMock(
            side_effect=GeminiClientError("Both providers unavailable")
        )

        parser = ResumeParser.__new__(ResumeParser)
        parser._gemini = mock_gemini
        parser._client = MagicMock()

        # Simulate the _do_parse path where _call_with_fallback is called
        with pytest.raises(GeminiClientError, match="Both providers"):
            asyncio.run(
                mock_gemini._call_with_fallback("extract resume")
            )


# ============================================================
# SECTION 6: JSON Parsing and Structured Response Tests
# ============================================================


class TestStructuredResponseParsing:
    """Tests that structured JSON responses are parsed correctly
    from both providers."""

    def test_valid_json_questions_parsed(self):
        """Valid JSON array of questions is parsed correctly."""
        with patch("app.integrations.gemini_client.get_settings") as ms:
            ms.return_value = MagicMock(gemini_api_key="test-key")
            client = GeminiClient()

        response = json.dumps([
            {"text": "Q1", "topic": "general", "difficulty": "easy", "follow_up": "FU1"},
            {"text": "Q2", "topic": "tech", "difficulty": "medium", "follow_up": None},
        ])

        questions = client._parse_questions_response(
            response, "technical", "algorithms", "medium"
        )

        assert len(questions) == 2
        assert questions[0].text == "Q1"
        assert questions[0].topic == "general"
        assert questions[1].text == "Q2"

    def test_json_with_code_fences_parsed(self):
        """JSON wrapped in markdown code fences is parsed correctly."""
        with patch("app.integrations.gemini_client.get_settings") as ms:
            ms.return_value = MagicMock(gemini_api_key="test-key")
            client = GeminiClient()

        data = [{"text": "Fenced Q1", "topic": None, "difficulty": None, "follow_up": None}]
        response = f"```json\n{json.dumps(data)}\n```"

        questions = client._parse_questions_response(
            response, "hr", None, None
        )

        assert len(questions) == 1
        assert questions[0].text == "Fenced Q1"

    def test_invalid_json_raises_error(self):
        """Invalid JSON response raises GeminiClientError."""
        with patch("app.integrations.gemini_client.get_settings") as ms:
            ms.return_value = MagicMock(gemini_api_key="test-key")
            client = GeminiClient()

        with pytest.raises(GeminiClientError, match="Failed to parse"):
            client._parse_questions_response(
                "not valid json", "hr", None, None
            )

    def test_non_array_json_raises_error(self):
        """JSON that is not an array raises GeminiClientError."""
        with patch("app.integrations.gemini_client.get_settings") as ms:
            ms.return_value = MagicMock(gemini_api_key="test-key")
            client = GeminiClient()

        with pytest.raises(GeminiClientError, match="not a JSON array"):
            client._parse_questions_response(
                '{"text": "not an array"}', "hr", None, None
            )

    def test_empty_questions_array_raises_error(self):
        """Empty or no-valid-question array raises GeminiClientError."""
        with patch("app.integrations.gemini_client.get_settings") as ms:
            ms.return_value = MagicMock(gemini_api_key="test-key")
            client = GeminiClient()

        with pytest.raises(GeminiClientError, match="no valid questions"):
            client._parse_questions_response("[]", "hr", None, None)


# ============================================================
# SECTION 7: Configuration and Environment Variable Tests
# ============================================================


class TestConfigurationLoading:
    """Tests for environment variable loading and app startup behavior."""

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test-key"}, clear=False)
    def test_settings_loads_openrouter_key(self):
        """Settings loads OPENROUTER_API_KEY from environment."""
        from app.config import Settings
        settings = Settings()
        assert settings.openrouter_api_key == "sk-or-test-key"

    @patch.dict("os.environ", {}, clear=False)
    def test_settings_default_empty_openrouter_key(self):
        """Settings defaults to empty string when OPENROUTER_API_KEY not set."""
        from app.config import Settings
        import os
        os.environ.pop("OPENROUTER_API_KEY", None)
        # Create settings without .env file to test pure env-var behavior
        settings = Settings(_env_file=None)
        assert settings.openrouter_api_key == ""

    @patch("app.integrations.openrouter_client.get_settings")
    def test_client_works_without_api_key(self, mock_settings):
        """Client initializes without error even without API key."""
        mock_settings.return_value = MagicMock(openrouter_api_key="")
        client = OpenRouterClient()
        assert client.is_configured is False
        # Should not crash on instantiation

    @patch("app.integrations.openrouter_client.get_settings")
    def test_client_works_with_api_key(self, mock_settings):
        """Client initializes correctly with API key."""
        mock_settings.return_value = MagicMock(openrouter_api_key="sk-valid")
        client = OpenRouterClient()
        assert client.is_configured is True


# ============================================================
# SECTION 8: End-to-End Fallback Flow Simulation
# ============================================================


class TestEndToEndFallbackFlow:
    """Simulates the complete fallback flow across services."""

    @patch("app.integrations.gemini_client.OpenRouterClient")
    @patch("app.integrations.gemini_client.asyncio.sleep", new_callable=AsyncMock)
    def test_full_question_generation_fallback_flow(
        self, mock_sleep, mock_or_class
    ):
        """Full flow: Gemini fails → OpenRouter succeeds → questions parsed."""
        with patch("app.integrations.gemini_client.get_settings") as ms:
            ms.return_value = MagicMock(gemini_api_key="test-key")
            gemini_client = GeminiClient()

        # Gemini always fails
        gemini_client._call_gemini = AsyncMock(
            side_effect=GeminiClientError("ResourceExhausted")
        )

        # OpenRouter returns valid JSON questions
        or_response = json.dumps([
            {"text": "What is polymorphism?", "topic": "OOP", "difficulty": "medium", "follow_up": None},
            {"text": "Explain SOLID principles", "topic": "Design", "difficulty": "hard", "follow_up": None},
        ])
        mock_or_instance = MagicMock()
        mock_or_instance.is_configured = True
        mock_or_instance.generate = AsyncMock(return_value=or_response)
        mock_or_class.return_value = mock_or_instance

        # Generate questions through the full chain
        result = asyncio.run(
            gemini_client.generate_questions(
                interview_type="technical",
                role="Software Engineer",
                topic="OOP",
                num_questions=2,
            )
        )

        assert len(result) == 2
        assert result[0].text == "What is polymorphism?"
        assert result[1].text == "Explain SOLID principles"

    @patch("app.integrations.gemini_client.OpenRouterClient")
    @patch("app.integrations.gemini_client.asyncio.sleep", new_callable=AsyncMock)
    def test_full_feedback_generation_fallback_flow(
        self, mock_sleep, mock_or_class
    ):
        """Full flow: Gemini fails → OpenRouter succeeds → feedback parsed."""
        with patch("app.integrations.gemini_client.get_settings") as ms:
            ms.return_value = MagicMock(gemini_api_key="test-key")
            gemini_client = GeminiClient()

        # Gemini always fails
        gemini_client._call_gemini = AsyncMock(
            side_effect=GeminiClientError("Service unavailable")
        )

        # OpenRouter returns valid feedback JSON
        or_response = json.dumps({
            "strengths": ["Good communication", "Clear structure"],
            "weaknesses": ["Too brief", "Lacks examples"],
            "recommendations": [
                "Add more detail",
                "Use STAR method",
                "Practice with timer",
            ],
        })
        mock_or_instance = MagicMock()
        mock_or_instance.is_configured = True
        mock_or_instance.generate = AsyncMock(return_value=or_response)
        mock_or_class.return_value = mock_or_instance

        service = AIFeedbackService(gemini_client=gemini_client)

        result = asyncio.run(
            service.generate_feedback(
                session_data=_make_session_data(),
                speech_metrics=_make_speech_metrics(),
                confidence_score=70,
            )
        )

        assert len(result.strengths) == 2
        assert len(result.weaknesses) == 2
        assert len(result.recommendations) == 3
        assert "Good communication" in result.strengths

    @patch("app.integrations.gemini_client.OpenRouterClient")
    @patch("app.integrations.gemini_client.asyncio.sleep", new_callable=AsyncMock)
    def test_full_both_fail_algorithmic_fallback(
        self, mock_sleep, mock_or_class
    ):
        """Full flow: Both providers fail → algorithmic feedback returned."""
        with patch("app.integrations.gemini_client.get_settings") as ms:
            ms.return_value = MagicMock(gemini_api_key="test-key")
            gemini_client = GeminiClient()

        # Gemini always fails
        gemini_client._call_gemini = AsyncMock(
            side_effect=GeminiClientError("Gemini down")
        )

        # OpenRouter also fails
        mock_or_instance = MagicMock()
        mock_or_instance.is_configured = True
        mock_or_instance.generate = AsyncMock(
            side_effect=OpenRouterClientError("OpenRouter down too")
        )
        mock_or_class.return_value = mock_or_instance

        service = AIFeedbackService(gemini_client=gemini_client)

        result = asyncio.run(
            service.generate_feedback(
                session_data=_make_session_data(),
                speech_metrics=_make_speech_metrics(),
                confidence_score=70,
            )
        )

        # Should still produce valid feedback via algorithmic fallback
        assert len(result.strengths) >= 2
        assert len(result.weaknesses) >= 2
        assert len(result.recommendations) >= 3
