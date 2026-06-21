"""Presentation session service for presentation-specific analysis.

Analyzes presentation recordings for speaking speed, clarity, structure,
communication, and engagement. Layers presentation-specific scoring on
top of the base SpeechAnalysisService metrics.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.integrations.gemini_client import GeminiClient, GeminiClientError
from app.integrations.supabase_client import get_supabase_client
from app.models.feedback import FeedbackReport, PresentationScores
from app.repositories.session_repository import RepositoryError, SessionRepository
from app.services.materials_parser import MaterialsContent, MaterialsParser
from app.services.speech_analysis_service import SpeechAnalysisService
from app.services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)

# Timeout for AI analysis (seconds)
# Increased to 90s to handle longer transcripts from 20-minute presentations
ANALYSIS_TIMEOUT = 90.0


class PresentationServiceError(Exception):
    """Raised when a presentation service operation fails."""

    pass


class PresentationNotFoundError(PresentationServiceError):
    """Raised when a presentation session is not found or not owned by user."""

    pass


class PresentationService:
    """Service for presentation session lifecycle and analysis.

    Handles:
    - Creating presentation sessions
    - Uploading recordings to storage
    - Uploading materials (PPT/PDF) to storage
    - Completing sessions with presentation-specific scoring
    """

    def __init__(
        self,
        repository: Optional[SessionRepository] = None,
        speech_analysis: Optional[SpeechAnalysisService] = None,
        transcription: Optional[TranscriptionService] = None,
        gemini_client: Optional[GeminiClient] = None,
        materials_parser: Optional[MaterialsParser] = None,
    ) -> None:
        """Initialize the presentation service.

        Args:
            repository: Session repository for persistence.
            speech_analysis: Speech analysis service for base metrics.
            transcription: Transcription service for audio processing.
            gemini_client: Gemini client for AI-powered analysis.
            materials_parser: Parser for extracting content from PPT/PDF files.
        """
        self._repository = repository or SessionRepository()
        self._speech_analysis = speech_analysis or SpeechAnalysisService()
        self._transcription = transcription or TranscriptionService()
        self._gemini = gemini_client or GeminiClient()
        self._materials_parser = materials_parser or MaterialsParser()
        self._supabase = get_supabase_client()

    def create_session(
        self,
        user_id: str,
        title: Optional[str] = None,
        topic: Optional[str] = None,
        duration_estimate_minutes: Optional[int] = None,
    ) -> dict:
        """Create a new presentation session.

        Args:
            user_id: The authenticated user's ID.
            title: Optional presentation title.
            topic: Optional presentation topic.
            duration_estimate_minutes: Optional estimated duration.

        Returns:
            Created session record.

        Raises:
            PresentationServiceError: If creation fails.
        """
        session_data = {
            "user_id": user_id,
            "session_type": "presentation",
            "status": "in_progress",
            "role": title or "Presentation",
            "topic": topic,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            session = self._repository.create_session(session_data)
            return session
        except RepositoryError as e:
            logger.error("Failed to create presentation session: %s", str(e))
            raise PresentationServiceError(
                f"Failed to create presentation session: {e}"
            ) from e

    async def upload_recording(
        self,
        user_id: str,
        session_id: UUID,
        audio_data: bytes,
        filename: str,
    ) -> str:
        """Upload a presentation recording to storage.

        Activates audio recording and stores it in Supabase Storage.

        Args:
            user_id: The authenticated user's ID.
            session_id: The presentation session UUID.
            audio_data: Raw audio file bytes.
            filename: Original filename.

        Returns:
            Public URL of the uploaded recording.

        Raises:
            PresentationNotFoundError: If session not found or not owned.
            PresentationServiceError: If upload fails.
        """
        # Verify session exists and belongs to user
        session = self._repository.get_session(session_id, user_id)
        if not session:
            raise PresentationNotFoundError(
                f"Presentation session {session_id} not found"
            )

        # Upload to Supabase Storage
        storage_path = f"presentations/{user_id}/{session_id}/recording_{filename}"
        try:
            self._supabase.storage.from_("recordings").upload(
                storage_path, audio_data
            )
            # Get public URL
            url_response = self._supabase.storage.from_("recordings").get_public_url(
                storage_path
            )
            recording_url = url_response if isinstance(url_response, str) else str(url_response)

            # Update session with recording URL metadata
            self._repository.update_session(
                session_id,
                user_id,
                {"role": session.get("role", "Presentation")},
            )

            return recording_url
        except RepositoryError as e:
            raise PresentationServiceError(
                f"Failed to update session after recording upload: {e}"
            ) from e
        except Exception as e:
            logger.error("Failed to upload recording: %s", str(e))
            raise PresentationServiceError(
                f"Failed to upload recording: {e}"
            ) from e

    async def upload_materials(
        self,
        user_id: str,
        session_id: UUID,
        file_data: bytes,
        filename: str,
    ) -> str:
        """Upload presentation materials (PPT/PDF) to storage.

        Associates the materials with the presentation session.

        Args:
            user_id: The authenticated user's ID.
            session_id: The presentation session UUID.
            file_data: Raw file bytes.
            filename: Original filename.

        Returns:
            Public URL of the uploaded materials.

        Raises:
            PresentationNotFoundError: If session not found or not owned.
            PresentationServiceError: If upload fails.
        """
        # Verify session exists and belongs to user
        session = self._repository.get_session(session_id, user_id)
        if not session:
            raise PresentationNotFoundError(
                f"Presentation session {session_id} not found"
            )

        # Upload to Supabase Storage
        storage_path = f"presentations/{user_id}/{session_id}/materials_{filename}"
        try:
            self._supabase.storage.from_("materials").upload(
                storage_path, file_data
            )
            url_response = self._supabase.storage.from_("materials").get_public_url(
                storage_path
            )
            materials_url = url_response if isinstance(url_response, str) else str(url_response)

            return materials_url
        except Exception as e:
            logger.error("Failed to upload materials: %s", str(e))
            raise PresentationServiceError(
                f"Failed to upload materials: {e}"
            ) from e

    async def complete_session(
        self,
        user_id: str,
        session_id: UUID,
    ) -> dict:
        """Complete a presentation session and generate analysis report.

        Downloads the uploaded recording from Supabase Storage, transcribes it,
        runs speech analysis, then uses AI to evaluate the presentation across
        five categories: speaking speed, clarity, structure, communication,
        and engagement. Generates improvement feedback.

        Args:
            user_id: The authenticated user's ID.
            session_id: The presentation session UUID.

        Returns:
            Dict with session, scores, and feedback data.

        Raises:
            PresentationNotFoundError: If session not found or not owned.
            PresentationServiceError: If completion fails.
        """
        # Verify session exists and belongs to user
        session = self._repository.get_session(session_id, user_id)
        if not session:
            raise PresentationNotFoundError(
                f"Presentation session {session_id} not found"
            )

        if session.get("status") == "completed":
            raise PresentationServiceError(
                "Session is already completed"
            )

        # Attempt to download and transcribe the recording
        transcript = ""
        speech_metrics = None
        duration_seconds = 0.0
        materials_content: Optional[MaterialsContent] = None

        try:
            # Download recording from storage
            storage_prefix = f"presentations/{user_id}/{session_id}/"
            recording_data = await self._download_recording(storage_prefix)

            if recording_data:
                # Transcribe the recording
                transcription_result = await self._transcription.transcribe_audio_detailed(
                    recording_data, filename="recording.webm"
                )
                transcript = transcription_result.text
                logger.info(
                    "Presentation transcription completed: %d chars",
                    len(transcript),
                )

                # Use actual duration from transcription (Whisper reports it)
                if transcription_result.duration > 0:
                    duration_seconds = transcription_result.duration
                else:
                    # Fallback: estimate from word timestamps
                    if transcription_result.words:
                        duration_seconds = transcription_result.words[-1].end
                    else:
                        # Last resort: rough estimate for audio-only
                        # (video webm is ~500kbps, audio-only is ~16kbps)
                        duration_seconds = max(1.0, len(recording_data) / 64000.0)

                # Run speech analysis on the transcript
                if transcript.strip() and duration_seconds > 0:
                    speech_metrics = self._speech_analysis.analyze(
                        transcript, duration_seconds
                    )
                    logger.info(
                        "Speech analysis: WPM=%d, communication_score=%d, duration=%.1fs",
                        speech_metrics.wpm,
                        speech_metrics.communication_score,
                        duration_seconds,
                    )
        except Exception as e:
            logger.warning(
                "Recording transcription/analysis failed, will use AI-only evaluation: %s",
                str(e),
            )

        # Attempt to download and parse uploaded materials (PPT/PDF)
        try:
            materials_content = await self._download_and_parse_materials(
                user_id, session_id
            )
            if materials_content and not materials_content.error:
                logger.info(
                    "Materials parsed: %d slides (%s)",
                    materials_content.slide_count,
                    materials_content.format,
                )
        except Exception as e:
            logger.warning("Materials parsing failed: %s", str(e))

        # Check if transcript is meaningful — if not, user didn't speak
        has_meaningful_speech = bool(
            transcript.strip()
            and self._transcription.is_meaningful_transcript(transcript)
        )

        if not has_meaningful_speech:
            logger.info("No meaningful speech detected — returning zero scores")
            scores = PresentationScores(
                speaking_speed=0,
                clarity=0,
                structure=0,
                communication=0,
                engagement=0,
            )
            feedback = FeedbackReport(
                strengths=[
                    "Session was recorded successfully",
                    "Presentation materials were prepared (if uploaded)",
                ],
                weaknesses=[
                    "No speech was detected in the recording",
                    "The presentation cannot be evaluated without spoken content",
                ],
                recommendations=[
                    "Ensure your microphone is working and not muted before recording",
                    "Speak clearly and audibly throughout your presentation",
                    "Try recording again with the microphone positioned closer to you",
                ],
                presentation_scores=scores,
            )
        else:
            # Generate presentation scores and feedback
            try:
                scores = await self._analyze_presentation(
                    session, transcript, speech_metrics, materials_content
                )
                feedback = await self._generate_presentation_feedback(
                    session, scores, transcript, materials_content
                )
            except Exception as e:
                logger.warning(
                    "AI analysis failed, using algorithmic fallback: %s", str(e)
                )
                scores = self._generate_algorithmic_scores(session, speech_metrics)
                feedback = self._generate_algorithmic_feedback(scores)

        # Compute overall score as average of presentation categories
        overall_score = round(
            (
                scores.speaking_speed
                + scores.clarity
                + scores.structure
                + scores.communication
                + scores.engagement
            )
            / 5
        )

        # Compute duration from speech metrics if available
        final_duration = int(duration_seconds) if duration_seconds > 0 else None

        # Update session as completed
        now = datetime.now(timezone.utc).isoformat()
        updates = {
            "status": "completed",
            "overall_score": overall_score,
            "communication_score": scores.communication,
            "completed_at": now,
        }
        if final_duration:
            updates["duration_seconds"] = final_duration

        try:
            updated_session = self._repository.update_session(
                session_id, user_id, updates
            )
        except RepositoryError as e:
            raise PresentationServiceError(
                f"Failed to update session on completion: {e}"
            ) from e

        # Save feedback
        feedback_data = {
            "strengths": feedback.strengths,
            "weaknesses": feedback.weaknesses,
            "recommendations": feedback.recommendations,
            "presentation_scores": scores.model_dump(),
        }

        try:
            self._repository.create_session_feedback(session_id, feedback_data)
        except RepositoryError as e:
            logger.warning("Failed to save presentation feedback: %s", str(e))

        return {
            "session": updated_session,
            "scores": scores,
            "feedback": feedback,
        }

    async def _download_recording(self, storage_prefix: str) -> Optional[bytes]:
        """Download the recording from Supabase Storage.

        Looks for a file matching the recording pattern in the given prefix.

        Args:
            storage_prefix: The storage path prefix (presentations/{user}/{session}/).

        Returns:
            Raw bytes of the recording, or None if not found.
        """
        try:
            # List files in the session's storage folder
            files = self._supabase.storage.from_("recordings").list(storage_prefix)
            recording_file = None
            for f in files:
                name = f.get("name", "") if isinstance(f, dict) else getattr(f, "name", "")
                if name.startswith("recording_"):
                    recording_file = name
                    break

            if not recording_file:
                logger.warning("No recording file found at prefix: %s", storage_prefix)
                return None

            file_path = f"{storage_prefix}{recording_file}"
            data = self._supabase.storage.from_("recordings").download(file_path)
            logger.info("Downloaded recording: %s (%d bytes)", file_path, len(data))
            return data
        except Exception as e:
            logger.warning("Failed to download recording: %s", str(e))
            return None

    async def _download_and_parse_materials(
        self, user_id: str, session_id: UUID
    ) -> Optional[MaterialsContent]:
        """Download materials from storage and parse their content.

        Looks for uploaded materials (PPT/PDF) in the "materials" bucket,
        downloads the file, and extracts slide structure using MaterialsParser.

        Args:
            user_id: The authenticated user's ID.
            session_id: The presentation session UUID.

        Returns:
            MaterialsContent with extracted slides, or None if no materials uploaded.
        """
        storage_prefix = f"presentations/{user_id}/{session_id}/"
        try:
            files = self._supabase.storage.from_("materials").list(storage_prefix)
            materials_file = None
            for f in files:
                name = f.get("name", "") if isinstance(f, dict) else getattr(f, "name", "")
                if name.startswith("materials_"):
                    materials_file = name
                    break

            if not materials_file:
                logger.debug("No materials file found for session %s", session_id)
                return None

            file_path = f"{storage_prefix}{materials_file}"
            data = self._supabase.storage.from_("materials").download(file_path)
            logger.info("Downloaded materials: %s (%d bytes)", file_path, len(data))

            # Derive original filename from storage name (strip "materials_" prefix)
            original_filename = materials_file[len("materials_"):] if materials_file.startswith("materials_") else materials_file
            return self._materials_parser.parse(data, original_filename)

        except Exception as e:
            logger.warning("Failed to download/parse materials: %s", str(e))
            return None

    async def _analyze_presentation(
        self, session: dict, transcript: str = "", speech_metrics=None,
        materials: Optional[MaterialsContent] = None
    ) -> PresentationScores:
        """Analyze presentation using AI for category-specific scores.

        Uses Gemini to evaluate the presentation across five dimensions:
        speaking speed, clarity, structure, communication, and engagement.
        When a transcript and/or materials are available, the AI receives
        actual content for accurate evaluation.

        Args:
            session: The session record from the database.
            transcript: The transcribed speech content (if available).
            speech_metrics: Speech analysis metrics (if available).
            materials: Parsed slide content from uploaded PPT/PDF (if available).

        Returns:
            PresentationScores with per-category scores.
        """
        topic = session.get("topic", "General")
        title = session.get("role", "Presentation")

        # Build a context-rich prompt with the actual transcript
        transcript_section = ""
        if transcript.strip():
            # Truncate very long transcripts to fit prompt limits
            trimmed = transcript[:3000] if len(transcript) > 3000 else transcript
            transcript_section = (
                f"\n\nHere is the speaker's transcript:\n\"\"\"\n{trimmed}\n\"\"\"\n"
            )

        metrics_section = ""
        if speech_metrics:
            metrics_section = (
                f"\n\nMeasured speech metrics:\n"
                f"- Words per minute: {speech_metrics.wpm}\n"
                f"- Total words: {speech_metrics.total_words}\n"
                f"- Filler words: {speech_metrics.filler_word_count}\n"
                f"- Communication score (algorithmic): {speech_metrics.communication_score}/100\n"
                f"- WPM in ideal range (120-160): {speech_metrics.wpm_in_range}\n"
            )

        materials_section = ""
        if materials and not materials.error and materials.slides:
            materials_summary = materials.to_summary(max_slides=15)
            materials_section = (
                f"\n\nUploaded presentation slides:\n{materials_summary}\n"
                "\nIMPORTANT evaluation rules when slides are provided:\n"
                "- Evaluate 'structure' based on how well the speaker follows "
                "the slide order and covers slide topics. If the transcript is "
                "completely unrelated to the slides, structure should be 0-15.\n"
                "- Evaluate 'engagement' partly on whether the speaker expands "
                "on slide content rather than just reading it verbatim.\n"
                "- If the speaker's transcript does NOT match the slide content "
                "(talking about a completely different topic), give LOW scores "
                "for structure (0-15), communication (0-30), and engagement (0-20). "
                "The speaker failed to deliver the prepared presentation.\n"
            )

        prompt = (
            "You are an expert presentation coach. Analyze a presentation session "
            f"titled '{title}' on the topic '{topic}'.\n"
            f"{transcript_section}{metrics_section}{materials_section}\n"
            "Based on the transcript content, speech metrics, and slide materials above, "
            "score the presentation on 5 categories (each 0-100):\n"
            "1. speaking_speed: How appropriate is the pace? (ideal: 120-160 WPM)\n"
            "2. clarity: How clear, articulate, and easy to follow is the speaker?\n"
            "3. structure: How well-organized is the presentation flow? Does the speaker "
            "follow the slide progression logically?\n"
            "4. communication: How effective is the overall delivery and message?\n"
            "5. engagement: How engaging, dynamic, and compelling is the presentation? "
            "Does the speaker add value beyond just reading slides?\n\n"
            "IMPORTANT: Only evaluate what can be measured from the AUDIO transcript. "
            "Do NOT factor in eye contact, body language, gestures, or visual presence "
            "— we only have the spoken words, not video analysis.\n\n"
            "Return ONLY a JSON object with these five keys and integer values.\n"
            "Example: {\"speaking_speed\": 75, \"clarity\": 80, \"structure\": 70, "
            "\"communication\": 85, \"engagement\": 65}"
        )

        try:
            response = await asyncio.wait_for(
                self._gemini._call_openrouter_primary(prompt),
                timeout=ANALYSIS_TIMEOUT,
            )
            return self._parse_scores_response(response)
        except (asyncio.TimeoutError, GeminiClientError) as e:
            logger.warning("AI presentation analysis failed: %s", str(e))
            return self._generate_algorithmic_scores(session, speech_metrics)

    def _parse_scores_response(self, response_text: str) -> PresentationScores:
        """Parse AI response into PresentationScores.

        Args:
            response_text: Raw JSON response from the AI provider.

        Returns:
            Validated PresentationScores instance.

        Raises:
            ValueError: If response cannot be parsed.
        """
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
            raise ValueError(f"Failed to parse scores response: {e}") from e

        # Clamp values to 0-100 range
        def clamp(val: int) -> int:
            return max(0, min(100, int(val)))

        return PresentationScores(
            speaking_speed=clamp(data.get("speaking_speed", 50)),
            clarity=clamp(data.get("clarity", 50)),
            structure=clamp(data.get("structure", 50)),
            communication=clamp(data.get("communication", 50)),
            engagement=clamp(data.get("engagement", 50)),
        )

    def _generate_algorithmic_scores(self, session: dict, speech_metrics=None) -> PresentationScores:
        """Generate presentation scores algorithmically as fallback.

        When speech metrics are available, derives scores from actual
        measurements. Otherwise produces reasonable defaults.

        Args:
            session: The session record.
            speech_metrics: Optional SpeechMetrics from speech analysis.

        Returns:
            PresentationScores with algorithmically generated values.
        """
        if speech_metrics:
            # Derive speaking_speed score from WPM proximity to ideal range
            wpm = speech_metrics.wpm
            if 120 <= wpm <= 160:
                speed_score = 85 + min(15, (160 - abs(wpm - 140)))
            elif wpm < 120:
                speed_score = max(20, 85 - (120 - wpm))
            else:
                speed_score = max(20, 85 - (wpm - 160))

            # Communication from the algorithmic score
            comm_score = speech_metrics.communication_score

            # Clarity: based on filler word ratio (fewer fillers = clearer)
            if speech_metrics.total_words > 0:
                filler_ratio = speech_metrics.filler_word_count / speech_metrics.total_words
                clarity_score = max(20, min(90, round(90 - filler_ratio * 500)))
            else:
                clarity_score = 50

            # Structure and engagement are harder to measure algorithmically
            structure_score = min(75, max(40, comm_score - 5))
            engagement_score = min(70, max(35, comm_score - 10))

            return PresentationScores(
                speaking_speed=max(0, min(100, speed_score)),
                clarity=max(0, min(100, clarity_score)),
                structure=max(0, min(100, structure_score)),
                communication=max(0, min(100, comm_score)),
                engagement=max(0, min(100, engagement_score)),
            )

        # Default to moderate scores when no metrics available
        return PresentationScores(
            speaking_speed=65,
            clarity=60,
            structure=55,
            communication=60,
            engagement=50,
        )

    async def _generate_presentation_feedback(
        self, session: dict, scores: PresentationScores, transcript: str = "",
        materials: Optional[MaterialsContent] = None
    ) -> FeedbackReport:
        """Generate AI-powered presentation feedback.

        Args:
            session: The session record.
            scores: Computed presentation scores.
            transcript: The transcribed speech content (if available).
            materials: Parsed slide content from uploaded PPT/PDF (if available).

        Returns:
            FeedbackReport with presentation-specific feedback.
        """
        topic = session.get("topic", "General")
        title = session.get("role", "Presentation")

        transcript_section = ""
        if transcript.strip():
            trimmed = transcript[:2000] if len(transcript) > 2000 else transcript
            transcript_section = (
                f"\n\nSpeaker's transcript excerpt:\n\"\"\"\n{trimmed}\n\"\"\"\n"
            )

        materials_section = ""
        if materials and not materials.error and materials.slides:
            materials_summary = materials.to_summary(max_slides=10)
            materials_section = (
                f"\n\nPresentation slides:\n{materials_summary}\n"
                "\nInclude feedback on how well the speaker followed their slides. "
                "If the speaker talked about a completely different topic than "
                "what the slides cover, clearly state this as a major weakness "
                "and recommend the speaker practice with their actual slides. "
                "Also note any slides that were skipped, and whether the speaker "
                "added insights beyond the slide content.\n"
            )

        prompt = (
            "You are an expert presentation coach. Based on the following scores "
            f"for a presentation titled '{title}' on '{topic}':\n\n"
            f"- Speaking Speed: {scores.speaking_speed}/100\n"
            f"- Clarity: {scores.clarity}/100\n"
            f"- Structure: {scores.structure}/100\n"
            f"- Communication: {scores.communication}/100\n"
            f"- Engagement: {scores.engagement}/100\n"
            f"{transcript_section}{materials_section}\n"
            "Generate a JSON object with:\n"
            '- "strengths": array of strings (minimum 2) - specific things done well\n'
            '- "weaknesses": array of strings (minimum 2) - areas needing improvement\n'
            '- "recommendations": array of strings (minimum 3) - actionable advice\n\n'
            "Focus on presentation-specific improvements for speed, clarity, "
            "structure, communication, and engagement. Reference specific parts "
            "of the transcript and slide content where possible.\n"
            "IMPORTANT: Only evaluate what can be measured from the AUDIO transcript. "
            "Do NOT mention eye contact, body language, gestures, facial expressions, "
            "or any visual elements — we only have audio data, not video analysis.\n"
            "Return ONLY the JSON object, no other text."
        )

        try:
            response = await asyncio.wait_for(
                self._gemini._call_openrouter_primary(prompt),
                timeout=ANALYSIS_TIMEOUT,
            )
            return self._parse_feedback_response(response, scores)
        except (asyncio.TimeoutError, GeminiClientError) as e:
            logger.warning("AI feedback generation failed: %s", str(e))
            return self._generate_algorithmic_feedback(scores)

    def _parse_feedback_response(
        self, response_text: str, scores: PresentationScores
    ) -> FeedbackReport:
        """Parse AI feedback response into FeedbackReport.

        Args:
            response_text: Raw JSON response from the AI provider.
            scores: The presentation scores for the report.

        Returns:
            Validated FeedbackReport with presentation_scores.

        Raises:
            ValueError: If response cannot be parsed.
        """
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return self._generate_algorithmic_feedback(scores)

        strengths = data.get("strengths", [])
        weaknesses = data.get("weaknesses", [])
        recommendations = data.get("recommendations", [])

        # Ensure minimums
        if not isinstance(strengths, list) or len(strengths) < 2:
            return self._generate_algorithmic_feedback(scores)
        if not isinstance(weaknesses, list) or len(weaknesses) < 2:
            return self._generate_algorithmic_feedback(scores)
        if not isinstance(recommendations, list) or len(recommendations) < 3:
            return self._generate_algorithmic_feedback(scores)

        return FeedbackReport(
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            presentation_scores=scores,
        )

    def _generate_algorithmic_feedback(
        self, scores: PresentationScores
    ) -> FeedbackReport:
        """Generate feedback algorithmically from presentation scores.

        Produces deterministic feedback based on score categories.

        Args:
            scores: Computed presentation scores.

        Returns:
            FeedbackReport with algorithmic presentation feedback.
        """
        strengths: list[str] = []
        weaknesses: list[str] = []
        recommendations: list[str] = []

        # Analyze each category for strengths/weaknesses
        if scores.speaking_speed >= 70:
            strengths.append(
                "Good speaking pace that keeps the audience engaged"
            )
        else:
            weaknesses.append(
                "Speaking pace could be improved for better audience engagement"
            )
            recommendations.append(
                "Practice delivering at 120-160 words per minute for optimal clarity"
            )

        if scores.clarity >= 70:
            strengths.append(
                "Clear and articulate delivery with good pronunciation"
            )
        else:
            weaknesses.append(
                "Clarity needs improvement — some points may be unclear to the audience"
            )
            recommendations.append(
                "Focus on enunciating key terms and using shorter, clearer sentences"
            )

        if scores.structure >= 70:
            strengths.append(
                "Well-organized presentation with logical flow"
            )
        else:
            weaknesses.append(
                "Presentation structure could be more organized"
            )
            recommendations.append(
                "Use a clear introduction-body-conclusion framework with transitions"
            )

        if scores.communication >= 70:
            strengths.append(
                "Effective communication style that connects with the audience"
            )
        else:
            weaknesses.append(
                "Overall communication effectiveness needs improvement"
            )
            recommendations.append(
                "Practice active engagement techniques like rhetorical questions "
                "and storytelling"
            )

        if scores.engagement >= 70:
            strengths.append(
                "Engaging delivery that maintains audience attention"
            )
        else:
            weaknesses.append(
                "Audience engagement could be higher"
            )
            recommendations.append(
                "Incorporate varied vocal tone, pauses for emphasis, and "
                "audience interaction points"
            )

        # Ensure minimums with varied messages (no duplicates)
        strength_fillers = [
            "Completed the presentation demonstrating commitment to improvement",
            "Shows a strong foundation for further presentation development",
        ]
        weakness_fillers = [
            "Consider adding more concrete examples to strengthen key points",
            "Practice varying vocal tone to add emphasis on important concepts",
        ]
        recommendation_fillers = [
            "Record yourself practicing and review to identify subtle improvement areas",
            "Ask a colleague for feedback on your next practice run",
            "Try presenting to a small group before delivering to a larger audience",
        ]

        filler_idx = 0
        while len(strengths) < 2:
            strengths.append(strength_fillers[filler_idx % len(strength_fillers)])
            filler_idx += 1

        filler_idx = 0
        while len(weaknesses) < 2:
            weaknesses.append(weakness_fillers[filler_idx % len(weakness_fillers)])
            filler_idx += 1

        filler_idx = 0
        while len(recommendations) < 3:
            recommendations.append(recommendation_fillers[filler_idx % len(recommendation_fillers)])
            filler_idx += 1

        return FeedbackReport(
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            presentation_scores=scores,
        )
