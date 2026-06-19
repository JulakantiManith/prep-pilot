"""AI feedback generation service using Gemini API.

Generates comprehensive session feedback including strengths, weaknesses,
and recommendations based on session data, speech metrics, and confidence scores.
Falls back to algorithmic feedback when AI generation fails.

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 9.3
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.integrations.gemini_client import GeminiClient, GeminiClientError
from app.models.answer import SpeechMetrics
from app.models.feedback import FeedbackReport
from app.models.session import InterviewType
from app.services.gemini_usage_tracker import (
    FeedbackSource,
    RequestType,
    usage_tracker,
)

logger = logging.getLogger(__name__)

# Timeout for feedback generation (seconds) - Requirement 10.4
REQUEST_TIMEOUT = 45.0

# Retry configuration matching GeminiClient pattern
MAX_RETRIES = 1
BASE_BACKOFF_SECONDS = 2.0


@dataclass
class AnswerData:
    """Data for a single answer within a session."""

    question_text: str
    transcript: str
    communication_score: Optional[int] = None
    confidence_score: Optional[int] = None


@dataclass
class SessionData:
    """Structured session input data for feedback generation."""

    interview_type: InterviewType
    role: str
    topic: Optional[str] = None
    difficulty: Optional[str] = None
    answers: list[AnswerData] = field(default_factory=list)


class AIFeedbackService:
    """Generates AI-powered feedback reports for interview sessions.

    Uses Gemini API to produce contextual strengths, weaknesses, and
    recommendations. Falls back to algorithmic feedback generation
    from metrics when AI is unavailable.

    Implements:
    - 1 retry with exponential backoff on failure
    - 45-second timeout per request
    - Algorithmic fallback when Gemini fails
    - Structured logging for monitoring AI provider failures
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None) -> None:
        """Initialize the feedback service.

        Args:
            gemini_client: Gemini API client instance. Creates default if None.
        """
        self._gemini = gemini_client or GeminiClient()

    async def generate_feedback(
        self,
        session_data: SessionData,
        speech_metrics: SpeechMetrics,
        confidence_score: int,
        session_id: Optional[str] = None,
    ) -> FeedbackReport:
        """Generate a feedback report for a completed session.

        Sends ALL session data to Gemini in ONE request at session end.
        No Gemini calls happen during the interview session itself.
        Falls back to algorithmic feedback if AI generation fails.

        Args:
            session_data: Session context including interview type, role, answers.
            speech_metrics: Aggregated speech metrics for the session.
            confidence_score: Overall confidence score (0-100).
            session_id: Optional session ID for usage tracking.

        Returns:
            FeedbackReport with strengths, weaknesses, and recommendations.
        """
        try:
            report = await self._generate_ai_feedback(
                session_data, speech_metrics, confidence_score, session_id
            )
            usage_tracker.record_feedback_source(
                FeedbackSource.GEMINI_AI, session_id
            )
            return report
        except (GeminiClientError, asyncio.TimeoutError, Exception) as e:
            logger.error(
                "AI feedback generation failed after retries, "
                "falling back to algorithmic feedback: %s",
                str(e),
            )
            usage_tracker.record_feedback_source(
                FeedbackSource.ALGORITHMIC_FALLBACK, session_id
            )
            return self._generate_algorithmic_feedback(
                session_data, speech_metrics, confidence_score
            )

    async def _generate_ai_feedback(
        self,
        session_data: SessionData,
        speech_metrics: SpeechMetrics,
        confidence_score: int,
        session_id: Optional[str] = None,
    ) -> FeedbackReport:
        """Generate feedback using Gemini API with retry logic.

        Sends everything in ONE request: all questions, answers, metrics,
        confidence, and session context. This is the only Gemini call
        for the feedback phase.

        Args:
            session_data: Session context.
            speech_metrics: Speech delivery metrics.
            confidence_score: Confidence score (0-100).
            session_id: Optional session ID for usage tracking.

        Returns:
            FeedbackReport parsed from Gemini response.

        Raises:
            GeminiClientError: If all retries are exhausted.
        """
        prompt = self._build_feedback_prompt(
            session_data, speech_metrics, confidence_score
        )
        estimated_input_tokens = len(prompt) // 4

        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                response_text = await self._call_gemini(prompt)
                report = self._parse_feedback_response(
                    response_text, session_data, confidence_score
                )

                # Track successful request
                estimated_output_tokens = len(response_text) // 4
                usage_tracker.record_request(
                    request_type=RequestType.FEEDBACK_GENERATION,
                    success=True,
                    session_id=session_id,
                    estimated_input_tokens=estimated_input_tokens,
                    estimated_output_tokens=estimated_output_tokens,
                )

                return report
            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    "Feedback generation timed out (attempt %d/%d)",
                    attempt + 1,
                    MAX_RETRIES + 1,
                )
                if attempt < MAX_RETRIES:
                    backoff = BASE_BACKOFF_SECONDS * (2**attempt)
                    await asyncio.sleep(backoff)
            except (GeminiClientError, json.JSONDecodeError, ValueError) as e:
                last_error = e
                logger.warning(
                    "Feedback generation failed (attempt %d/%d): %s",
                    attempt + 1,
                    MAX_RETRIES + 1,
                    str(e),
                )
                if attempt < MAX_RETRIES:
                    backoff = BASE_BACKOFF_SECONDS * (2**attempt)
                    await asyncio.sleep(backoff)

        # Track failed request
        usage_tracker.record_request(
            request_type=RequestType.FEEDBACK_GENERATION,
            success=False,
            session_id=session_id,
            estimated_input_tokens=estimated_input_tokens,
            error=str(last_error),
        )

        raise GeminiClientError(
            f"Feedback generation failed after {MAX_RETRIES + 1} attempts: {last_error}"
        )

    async def _call_gemini(self, prompt: str) -> str:
        """Make an AI API call using OpenRouter/free as primary provider.

        Uses OpenRouter directly for feedback generation to preserve
        Gemini quota for resume parsing. Falls back to Gemini if
        OpenRouter is unavailable.

        Args:
            prompt: Constructed feedback prompt.

        Returns:
            Raw text response from the provider.

        Raises:
            GeminiClientError: If both providers fail.
        """
        return await self._gemini._call_openrouter_primary(prompt)

    def _build_feedback_prompt(
        self,
        session_data: SessionData,
        speech_metrics: SpeechMetrics,
        confidence_score: int,
    ) -> str:
        """Build a structured prompt for Gemini feedback generation.

        Args:
            session_data: Session context.
            speech_metrics: Speech delivery metrics.
            confidence_score: Confidence score (0-100).

        Returns:
            Formatted prompt string for Gemini.
        """
        interview_type = session_data.interview_type.value
        role = session_data.role

        # Build answers summary
        answers_text = ""
        for i, answer in enumerate(session_data.answers, 1):
            answers_text += (
                f"\nQuestion {i}: {answer.question_text}\n"
                f"Answer: {answer.transcript}\n"
            )
            if answer.communication_score is not None:
                answers_text += (
                    f"Communication Score: {answer.communication_score}/100\n"
                )
            if answer.confidence_score is not None:
                answers_text += f"Confidence Score: {answer.confidence_score}/100\n"

        # Build type-specific evaluation instructions
        if session_data.interview_type == InterviewType.TECHNICAL:
            type_specific = (
                '\n- "technical_evaluation": an object with keys '
                '"accuracy" (string assessment of technical correctness), '
                '"completeness" (string assessment of answer completeness), '
                '"depth" (string assessment of technical depth), '
                '"score" (integer 0-100 for overall technical quality)'
            )
            eval_instruction = (
                "For this TECHNICAL interview, evaluate the technical accuracy "
                "and correctness of the answers. Assess whether the candidate "
                "demonstrates proper understanding of technical concepts."
            )
        else:
            type_specific = ""
            eval_instruction = (
                "For this non-technical interview, evaluate the communication "
                "structure and logical flow of the answers. Assess whether the "
                "candidate organizes their responses clearly and presents ideas "
                "in a coherent, structured manner (e.g., using STAR method)."
            )

        # Confidence-specific instruction
        confidence_instruction = ""
        if 1 <= confidence_score <= 49:
            confidence_instruction = (
                "\nIMPORTANT: The candidate's confidence score is LOW "
                f"({confidence_score}/100). You MUST include at least one "
                "specific recommendation for improving confidence in the "
                "recommendations array."
            )

        prompt = (
            f"You are an expert interview coach providing feedback for a "
            f"{interview_type} interview session for the role of {role}."
        )

        if session_data.topic:
            prompt += f"\nTopic: {session_data.topic}"
        if session_data.difficulty:
            prompt += f"\nDifficulty: {session_data.difficulty}"

        prompt += (
            f"\n\n{eval_instruction}"
            f"{confidence_instruction}"
            f"\n\nSession Speech Metrics:"
            f"\n- Words per minute: {speech_metrics.wpm}"
            f"\n- Total words: {speech_metrics.total_words}"
            f"\n- Filler word count: {speech_metrics.filler_word_count}"
            f"\n- Speaking duration: {speech_metrics.speaking_duration:.1f}s"
            f"\n- Average pause duration: {speech_metrics.avg_pause_duration:.3f}s"
            f"\n- Communication score: {speech_metrics.communication_score}/100"
            f"\n- WPM in ideal range (120-160): {speech_metrics.wpm_in_range}"
            f"\n- Confidence score: {confidence_score}/100"
            f"\n\nAnswers:{answers_text}"
            f"\n\nGenerate a JSON object with the following fields:"
            f'\n- "strengths": array of strings (minimum 2 items) - '
            f"specific things the candidate did well"
            f'\n- "weaknesses": array of strings (minimum 2 items) - '
            f"specific areas needing improvement"
            f'\n- "recommendations": array of strings (minimum 3 items) - '
            f"actionable advice for improvement"
            f"{type_specific}"
            f"\n\nReturn ONLY the JSON object, no other text or markdown formatting."
        )

        return prompt

    def _parse_feedback_response(
        self,
        response_text: str,
        session_data: SessionData,
        confidence_score: int,
    ) -> FeedbackReport:
        """Parse Gemini's JSON response into a FeedbackReport.

        Ensures minimum counts are met and applies post-processing rules.

        Args:
            response_text: Raw response text from Gemini.
            session_data: Session context for type-specific handling.
            confidence_score: For confidence recommendation enforcement.

        Returns:
            Validated FeedbackReport.

        Raises:
            GeminiClientError: If response cannot be parsed or validated.
        """
        # Strip markdown code fences if present
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise GeminiClientError(
                f"Failed to parse feedback response as JSON: {e}"
            ) from e

        if not isinstance(data, dict):
            raise GeminiClientError("Feedback response is not a JSON object")

        strengths = data.get("strengths", [])
        weaknesses = data.get("weaknesses", [])
        recommendations = data.get("recommendations", [])

        # Ensure minimums are met
        if not isinstance(strengths, list) or len(strengths) < 2:
            raise GeminiClientError(
                f"Insufficient strengths: got {len(strengths) if isinstance(strengths, list) else 0}, need 2"
            )
        if not isinstance(weaknesses, list) or len(weaknesses) < 2:
            raise GeminiClientError(
                f"Insufficient weaknesses: got {len(weaknesses) if isinstance(weaknesses, list) else 0}, need 2"
            )
        if not isinstance(recommendations, list) or len(recommendations) < 3:
            raise GeminiClientError(
                f"Insufficient recommendations: got {len(recommendations) if isinstance(recommendations, list) else 0}, need 3"
            )

        # Ensure confidence recommendation when score is 1-49
        if 1 <= confidence_score <= 49:
            has_confidence_rec = any(
                "confidence" in rec.lower() for rec in recommendations
            )
            if not has_confidence_rec:
                recommendations.append(
                    "Practice speaking with a steady pace and minimize hesitations "
                    "to project more confidence. Record yourself and review to "
                    "identify nervous habits."
                )

        # Build technical evaluation for technical interviews
        technical_evaluation: Optional[dict[str, Any]] = None
        if session_data.interview_type == InterviewType.TECHNICAL:
            technical_evaluation = data.get("technical_evaluation")
            if technical_evaluation is None:
                technical_evaluation = {
                    "accuracy": "Unable to evaluate",
                    "completeness": "Unable to evaluate",
                    "depth": "Unable to evaluate",
                    "score": 50,
                }

        return FeedbackReport(
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            technical_evaluation=technical_evaluation,
            presentation_scores=None,
        )

    def _generate_algorithmic_feedback(
        self,
        session_data: SessionData,
        speech_metrics: SpeechMetrics,
        confidence_score: int,
    ) -> FeedbackReport:
        """Generate feedback algorithmically from metrics when AI fails.

        Produces deterministic feedback based on speech metrics and
        confidence scores without relying on an AI provider.

        Args:
            session_data: Session context.
            speech_metrics: Speech delivery metrics.
            confidence_score: Confidence score (0-100).

        Returns:
            FeedbackReport generated from metric analysis.
        """
        strengths = self._compute_strengths(speech_metrics, confidence_score)
        weaknesses = self._compute_weaknesses(speech_metrics, confidence_score)
        recommendations = self._compute_recommendations(
            session_data, speech_metrics, confidence_score
        )

        # Build technical evaluation for technical interviews
        technical_evaluation: Optional[dict[str, Any]] = None
        if session_data.interview_type == InterviewType.TECHNICAL:
            technical_evaluation = {
                "accuracy": "Unable to evaluate without AI analysis",
                "completeness": "Unable to evaluate without AI analysis",
                "depth": "Unable to evaluate without AI analysis",
                "score": speech_metrics.communication_score,
            }

        return FeedbackReport(
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            technical_evaluation=technical_evaluation,
            presentation_scores=None,
        )

    def _compute_strengths(
        self, speech_metrics: SpeechMetrics, confidence_score: int
    ) -> list[str]:
        """Compute strengths from metrics.

        Always returns at least 2 strengths.

        Args:
            speech_metrics: Speech delivery metrics.
            confidence_score: Confidence score (0-100).

        Returns:
            List of strength descriptions (minimum 2).
        """
        strengths: list[str] = []

        if speech_metrics.wpm_in_range:
            strengths.append(
                f"Good speaking pace at {speech_metrics.wpm} WPM, "
                f"within the ideal range of 120-160 WPM"
            )

        if speech_metrics.filler_word_count == 0:
            strengths.append(
                "Excellent verbal clarity with no filler words detected"
            )
        elif speech_metrics.total_words > 0:
            filler_ratio = speech_metrics.filler_word_count / speech_metrics.total_words
            if filler_ratio < 0.03:
                strengths.append(
                    "Low filler word usage demonstrating good verbal preparation"
                )

        if confidence_score >= 70:
            strengths.append(
                f"Strong confidence in delivery (score: {confidence_score}/100)"
            )

        if speech_metrics.communication_score >= 75:
            strengths.append(
                f"Strong communication skills "
                f"(score: {speech_metrics.communication_score}/100)"
            )

        if speech_metrics.avg_pause_duration <= 0.5:
            strengths.append("Natural speech flow with minimal pauses")

        # Ensure minimum 2 strengths
        if len(strengths) < 2:
            if speech_metrics.total_words > 50:
                strengths.append(
                    "Provided substantive responses with adequate detail"
                )
            if len(strengths) < 2:
                strengths.append(
                    "Completed the session demonstrating engagement with the material"
                )

        return strengths

    def _compute_weaknesses(
        self, speech_metrics: SpeechMetrics, confidence_score: int
    ) -> list[str]:
        """Compute weaknesses from metrics.

        Always returns at least 2 weaknesses.

        Args:
            speech_metrics: Speech delivery metrics.
            confidence_score: Confidence score (0-100).

        Returns:
            List of weakness descriptions (minimum 2).
        """
        weaknesses: list[str] = []

        if not speech_metrics.wpm_in_range:
            if speech_metrics.wpm < 120:
                weaknesses.append(
                    f"Speaking pace too slow at {speech_metrics.wpm} WPM "
                    f"(ideal: 120-160 WPM), which may indicate hesitation"
                )
            else:
                weaknesses.append(
                    f"Speaking pace too fast at {speech_metrics.wpm} WPM "
                    f"(ideal: 120-160 WPM), which may reduce clarity"
                )

        if speech_metrics.total_words > 0:
            filler_ratio = speech_metrics.filler_word_count / speech_metrics.total_words
            if filler_ratio >= 0.05:
                weaknesses.append(
                    f"High filler word usage ({speech_metrics.filler_word_count} "
                    f"filler words) reduces perceived professionalism"
                )

        if confidence_score < 50:
            weaknesses.append(
                f"Low confidence score ({confidence_score}/100) suggests "
                f"nervousness or uncertainty in delivery"
            )

        if speech_metrics.avg_pause_duration > 1.5:
            weaknesses.append(
                f"Long average pauses ({speech_metrics.avg_pause_duration:.1f}s) "
                f"may indicate lack of preparation"
            )

        if speech_metrics.communication_score < 50:
            weaknesses.append(
                f"Communication score below average "
                f"({speech_metrics.communication_score}/100)"
            )

        # Ensure minimum 2 weaknesses
        while len(weaknesses) < 2:
            if (
                len(weaknesses) < 2
                and speech_metrics.communication_score < 80
                and not any("communication" in w.lower() for w in weaknesses)
            ):
                weaknesses.append(
                    "Communication delivery could be more polished and structured"
                )
            elif len(weaknesses) < 2 and not any(
                "structured" in w.lower() for w in weaknesses
            ):
                weaknesses.append(
                    "Consider providing more detailed and structured responses"
                )
            else:
                weaknesses.append(
                    "Practice articulating key points more concisely"
                )

        return weaknesses

    def _compute_recommendations(
        self,
        session_data: SessionData,
        speech_metrics: SpeechMetrics,
        confidence_score: int,
    ) -> list[str]:
        """Compute recommendations from metrics.

        Always returns at least 3 recommendations. Includes confidence
        improvement recommendation when score is 1-49 (Requirement 9.3).

        Args:
            session_data: Session context.
            speech_metrics: Speech delivery metrics.
            confidence_score: Confidence score (0-100).

        Returns:
            List of recommendation descriptions (minimum 3).
        """
        recommendations: list[str] = []

        # Confidence improvement recommendation (Requirement 9.3)
        if 1 <= confidence_score <= 49:
            recommendations.append(
                "Practice speaking with a steady pace and minimize hesitations "
                "to project more confidence. Record yourself and review to "
                "identify nervous habits."
            )

        if not speech_metrics.wpm_in_range:
            if speech_metrics.wpm < 120:
                recommendations.append(
                    "Practice speaking slightly faster to maintain engagement. "
                    "Try reading aloud at 130-140 WPM to build a natural faster pace."
                )
            else:
                recommendations.append(
                    "Slow down your speaking pace to improve clarity. "
                    "Practice deliberate pauses between key points."
                )

        if speech_metrics.filler_word_count > 3:
            recommendations.append(
                "Reduce filler words by pausing briefly instead of using "
                "'um', 'uh', or 'like'. Practice with conscious pauses."
            )

        # Type-specific recommendations
        if session_data.interview_type == InterviewType.TECHNICAL:
            recommendations.append(
                "Structure technical answers using a clear framework: "
                "state the concept, explain with examples, and discuss tradeoffs."
            )
        elif session_data.interview_type == InterviewType.BEHAVIORAL:
            recommendations.append(
                "Use the STAR method (Situation, Task, Action, Result) "
                "to structure behavioral answers for maximum impact."
            )
        elif session_data.interview_type == InterviewType.HR:
            recommendations.append(
                "Connect your answers to the specific role and company. "
                "Research common HR questions and prepare concise, relevant stories."
            )
        else:
            recommendations.append(
                "Structure your responses with a clear beginning, middle, and end. "
                "Lead with the key point and support with specifics."
            )

        if speech_metrics.avg_pause_duration > 1.0:
            recommendations.append(
                "Reduce pause duration by preparing key talking points before "
                "answering. A brief mental outline helps maintain flow."
            )

        if speech_metrics.communication_score < 70:
            recommendations.append(
                "Focus on improving overall communication delivery by "
                "practicing with a timer and self-recording regularly."
            )

        # Ensure minimum 3 recommendations
        while len(recommendations) < 3:
            recommendations.append(
                "Continue regular practice sessions to build consistency "
                "and comfort with the interview format."
            )

        return recommendations
