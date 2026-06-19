"""Answer relevance scoring service.

Evaluates whether interview answers actually address the questions asked.
Uses AI (Gemini with OpenRouter fallback) to score semantic alignment
between questions and responses at session completion time.

Scoring dimensions:
- Relevance: Does the answer address the specific question?
- Accuracy: Is the technical content correct? (for technical interviews)
- Completeness: Does the answer cover the key points expected?

This runs at session completion (batch), NOT per-answer, to avoid
latency during the interview flow.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from app.integrations.gemini_client import GeminiClient, GeminiClientError

logger = logging.getLogger(__name__)


@dataclass
class AnswerRelevanceResult:
    """Relevance scoring result for a single answer."""

    relevance_score: int  # 0-100: how well the answer addresses the question
    accuracy_score: Optional[int]  # 0-100: technical accuracy (None for non-technical)
    completeness_score: int  # 0-100: how thorough the answer is
    explanation: str  # Brief explanation of the scores


@dataclass
class SessionRelevanceResult:
    """Aggregate relevance scores for an entire session."""

    per_answer: list[AnswerRelevanceResult]
    avg_relevance: int
    avg_accuracy: Optional[int]  # None if non-technical
    avg_completeness: int


class RelevanceScorer:
    """Scores answer relevance using AI at session completion.

    Evaluates all answers in a single batch AI call to minimize
    API usage. Falls back gracefully if AI is unavailable.
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None) -> None:
        self._gemini = gemini_client or GeminiClient()

    async def score_session(
        self,
        answers: list[dict],
        interview_type: str,
        role: str,
        topic: Optional[str] = None,
    ) -> Optional[SessionRelevanceResult]:
        """Score all answers in a session for relevance and accuracy.

        Makes ONE AI call with all Q&A pairs. Returns None if scoring
        fails (non-fatal — session still completes without relevance scores).

        Args:
            answers: List of answer dicts with question_text and transcript.
            interview_type: Type of interview for context.
            role: Target role for context.
            topic: Optional topic for technical context.

        Returns:
            SessionRelevanceResult or None if scoring fails.
        """
        # Filter to answers with actual content
        scorable = [
            a for a in answers
            if a.get("transcript") and a.get("question_text")
            and len(a["transcript"].strip()) > 5
        ]

        if not scorable:
            logger.info("No scorable answers for relevance evaluation")
            return None

        prompt = self._build_scoring_prompt(
            scorable, interview_type, role, topic
        )

        try:
            response_text = await self._gemini._call_openrouter_primary(prompt)
            result = self._parse_scoring_response(response_text, len(scorable))
            logger.info(
                "Relevance scoring complete: avg_relevance=%d, avg_completeness=%d",
                result.avg_relevance,
                result.avg_completeness,
            )
            return result
        except (GeminiClientError, Exception) as e:
            logger.warning(
                "Relevance scoring failed (non-fatal): %s", str(e)
            )
            return None

    def _build_scoring_prompt(
        self,
        answers: list[dict],
        interview_type: str,
        role: str,
        topic: Optional[str],
    ) -> str:
        """Build the AI prompt for batch relevance scoring."""
        is_technical = interview_type in ("technical", "resume_based")

        qa_pairs = ""
        for i, a in enumerate(answers):
            qa_pairs += (
                f"\n--- Answer {i + 1} ---\n"
                f"Question: {a['question_text']}\n"
                f"Response: {a['transcript']}\n"
            )

        accuracy_instruction = ""
        accuracy_field = ""
        if is_technical:
            accuracy_instruction = (
                '\n- "accuracy": integer 0-100 — Is the technical content '
                "factually correct? 0 = completely wrong, 100 = fully accurate."
            )
            accuracy_field = ', "accuracy": <int>'

        return (
            f"You are evaluating interview answers for a {interview_type} interview "
            f"for the role of {role}."
            f"{f' Topic: {topic}.' if topic else ''}"
            f"\n\nFor each answer below, score these dimensions:"
            f'\n- "relevance": integer 0-100 — Does the answer actually address '
            f"the specific question asked? 0 = completely unrelated, "
            f"50 = partially addresses it, 100 = directly and fully addresses it."
            f"{accuracy_instruction}"
            f'\n- "completeness": integer 0-100 — How thorough is the answer? '
            f"Does it cover the key points expected? 0 = no useful content, "
            f"100 = comprehensive."
            f'\n- "explanation": string — One sentence explaining the scores.'
            f"\n\nHere are the Q&A pairs:{qa_pairs}"
            f"\n\nReturn a JSON array with one object per answer in order. "
            f"Each object must have: "
            f'"relevance": <int>{accuracy_field}, "completeness": <int>, '
            f'"explanation": <string>'
            f"\n\nReturn ONLY the JSON array, no other text."
        )

    def _parse_scoring_response(
        self, response_text: str, expected_count: int
    ) -> SessionRelevanceResult:
        """Parse the AI scoring response into structured results."""
        # Strip markdown code fences
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        # Try to find JSON array
        data = None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            start_idx = text.find("[")
            end_idx = text.rfind("]")
            if start_idx != -1 and end_idx != -1:
                try:
                    data = json.loads(text[start_idx:end_idx + 1])
                except json.JSONDecodeError:
                    pass

        if not data or not isinstance(data, list):
            raise ValueError(f"Could not parse relevance scores from response: {text[:200]}")

        per_answer: list[AnswerRelevanceResult] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            per_answer.append(AnswerRelevanceResult(
                relevance_score=self._clamp(item.get("relevance", 50)),
                accuracy_score=(
                    self._clamp(item["accuracy"])
                    if "accuracy" in item else None
                ),
                completeness_score=self._clamp(item.get("completeness", 50)),
                explanation=item.get("explanation", ""),
            ))

        # If we got fewer scores than answers, pad with defaults
        while len(per_answer) < expected_count:
            per_answer.append(AnswerRelevanceResult(
                relevance_score=50,
                accuracy_score=None,
                completeness_score=50,
                explanation="Score unavailable",
            ))

        # Compute averages
        avg_relevance = int(
            sum(a.relevance_score for a in per_answer) / len(per_answer)
        )
        avg_completeness = int(
            sum(a.completeness_score for a in per_answer) / len(per_answer)
        )

        accuracy_scores = [
            a.accuracy_score for a in per_answer if a.accuracy_score is not None
        ]
        avg_accuracy = (
            int(sum(accuracy_scores) / len(accuracy_scores))
            if accuracy_scores else None
        )

        return SessionRelevanceResult(
            per_answer=per_answer,
            avg_relevance=avg_relevance,
            avg_accuracy=avg_accuracy,
            avg_completeness=avg_completeness,
        )

    @staticmethod
    def _clamp(value: int) -> int:
        """Clamp a score to 0-100."""
        try:
            return max(0, min(100, int(value)))
        except (TypeError, ValueError):
            return 50
