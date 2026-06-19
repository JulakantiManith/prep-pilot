"""Resume parser service for extracting structured data from PDF/DOCX files.

Extracts skills, projects, experience, and education from uploaded resumes
using text extraction (PyPDF2/python-docx) followed by Gemini AI for
structured data extraction.

Includes confidence scoring and 60-second timeout.

Requirements: 6.1, 6.2, 6.3, 6.4
"""

import asyncio
import io
import json
import logging
from typing import Optional

from app.integrations.gemini_client import GeminiClient, GeminiClientError
from app.integrations.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Maximum time allowed for extraction (seconds)
EXTRACTION_TIMEOUT = 60.0


class ResumeParserError(Exception):
    """Raised when resume parsing fails."""

    pass


class ResumeParser:
    """Service for parsing resumes and extracting structured data.

    Flow:
    1. Download file from Supabase Storage
    2. Extract raw text from PDF or DOCX
    3. Send raw text to Gemini for structured extraction
    4. Return extracted data with confidence score
    5. Handle failures gracefully with clear error messages
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None) -> None:
        """Initialize the resume parser.

        Args:
            gemini_client: Optional Gemini client instance. Creates default if None.
        """
        self._gemini = gemini_client or GeminiClient()
        self._client = get_supabase_client()

    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract raw text from a PDF file.

        Args:
            file_content: Raw PDF file bytes.

        Returns:
            Extracted text string.

        Raises:
            ResumeParserError: If PDF text extraction fails.
        """
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(io.BytesIO(file_content))
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            text = "\n".join(text_parts).strip()
            if not text:
                raise ResumeParserError(
                    "Could not extract any text from the PDF file. "
                    "The file may be image-based or corrupted."
                )
            return text

        except ResumeParserError:
            raise
        except Exception as e:
            logger.error("PDF text extraction failed: %s", str(e))
            raise ResumeParserError(
                "Failed to read the PDF file. Please ensure it is a valid, "
                "text-based PDF document."
            ) from e

    def _extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract raw text from a DOCX file.

        Args:
            file_content: Raw DOCX file bytes.

        Returns:
            Extracted text string.

        Raises:
            ResumeParserError: If DOCX text extraction fails.
        """
        try:
            from docx import Document

            doc = Document(io.BytesIO(file_content))
            text_parts = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text.strip())

            text = "\n".join(text_parts).strip()
            if not text:
                raise ResumeParserError(
                    "Could not extract any text from the DOCX file. "
                    "The file may be empty or corrupted."
                )
            return text

        except ResumeParserError:
            raise
        except Exception as e:
            logger.error("DOCX text extraction failed: %s", str(e))
            raise ResumeParserError(
                "Failed to read the DOCX file. Please ensure it is a valid "
                "Word document."
            ) from e

    def _build_extraction_prompt(self, text: str) -> str:
        """Build the Gemini prompt for structured resume data extraction.

        Args:
            text: Raw text extracted from the resume.

        Returns:
            Formatted prompt string.
        """
        return (
            "Extract structured information from the following resume text. "
            "Return a JSON object with the following fields:\n\n"
            '- "skills": array of strings (technical and soft skills)\n'
            '- "projects": array of objects with fields: "name" (string), '
            '"description" (string), "technologies" (array of strings)\n'
            '- "experience": array of objects with fields: "title" (string), '
            '"company" (string), "duration" (string), "description" (string)\n'
            '- "education": array of objects with fields: "degree" (string), '
            '"institution" (string), "year" (string)\n'
            '- "confidence": a float between 0.0 and 1.0 indicating how confident '
            "you are in the extraction quality (1.0 = very confident, all sections "
            "clearly found; 0.5 = moderate, some sections unclear; below 0.3 = low, "
            "resume format is unusual or data is sparse)\n\n"
            "If a section cannot be found, return an empty array for that field.\n"
            "Return ONLY the JSON object, no other text or markdown formatting.\n\n"
            f"Resume text:\n{text}"
        )

    def _parse_extraction_response(self, response_text: str) -> dict:
        """Parse Gemini's extraction response into structured data.

        Args:
            response_text: Raw response from Gemini.

        Returns:
            Dictionary with extracted data and confidence score.

        Raises:
            ResumeParserError: If response cannot be parsed.
        """
        text = response_text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Gemini extraction response: %s", str(e))
            raise ResumeParserError(
                "Failed to extract structured data from the resume. "
                "Please try re-uploading a properly formatted resume."
            ) from e

        if not isinstance(data, dict):
            raise ResumeParserError(
                "Extraction returned unexpected format. "
                "Please try re-uploading a properly formatted resume."
            )

        # Normalize the response
        extracted = {
            "skills": data.get("skills", []),
            "projects": data.get("projects", []),
            "experience": data.get("experience", []),
            "education": data.get("education", []),
        }

        confidence = data.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        confidence = max(0.0, min(1.0, float(confidence)))

        return {
            "extracted_data": extracted,
            "confidence": confidence,
        }

    async def parse_resume(self, resume_id: str, user_id: str) -> dict:
        """Parse a resume and extract structured data.

        Downloads the file from storage, extracts text, and uses Gemini
        to extract structured information. Enforces 60-second timeout.

        Args:
            resume_id: The resume record ID.
            user_id: The authenticated user's ID (for ownership validation).

        Returns:
            Dictionary with extracted_data and confidence score.

        Raises:
            ResumeParserError: If parsing fails at any step.
        """
        try:
            return await asyncio.wait_for(
                self._do_parse(resume_id, user_id),
                timeout=EXTRACTION_TIMEOUT,
            )
        except asyncio.TimeoutError:
            # Update resume status to failed
            await self._update_resume_status(resume_id, "failed")
            logger.error(
                "Resume extraction timed out after %ds for resume %s",
                EXTRACTION_TIMEOUT,
                resume_id,
            )
            raise ResumeParserError(
                "Resume extraction timed out. Please try re-uploading "
                "a properly formatted resume."
            )

    async def _do_parse(self, resume_id: str, user_id: str) -> dict:
        """Internal parsing logic without timeout wrapper.

        Args:
            resume_id: The resume record ID.
            user_id: The authenticated user's ID.

        Returns:
            Dictionary with extracted_data and confidence score.

        Raises:
            ResumeParserError: If parsing fails.
        """
        # Fetch resume record
        resume_record = self._get_resume_record(resume_id, user_id)

        file_path = resume_record["file_path"]
        file_name = resume_record.get("file_name", "")

        # Update status to processing
        await self._update_resume_status(resume_id, "processing")

        # Download file from Supabase Storage
        file_content = self._download_file(file_path)

        # Extract raw text based on file type
        if file_name.lower().endswith(".pdf") or file_path.lower().endswith(".pdf"):
            raw_text = self._extract_text_from_pdf(file_content)
        elif file_name.lower().endswith(".docx") or file_path.lower().endswith(".docx"):
            raw_text = self._extract_text_from_docx(file_content)
        else:
            raise ResumeParserError(
                "Unsupported file format. Only PDF and DOCX files are accepted."
            )

        # Use Gemini (with OpenRouter fallback) to extract structured data
        prompt = self._build_extraction_prompt(raw_text)

        try:
            response_text = await self._gemini._call_with_fallback(prompt)

            if not response_text:
                raise ResumeParserError(
                    "AI extraction returned empty result. "
                    "Please try re-uploading a properly formatted resume."
                )

            result = self._parse_extraction_response(response_text)

        except ResumeParserError:
            await self._update_resume_status(resume_id, "failed")
            raise
        except GeminiClientError as e:
            await self._update_resume_status(resume_id, "failed")
            logger.error("AI extraction failed for resume %s: %s", resume_id, str(e))
            raise ResumeParserError(
                "Failed to extract data from the resume. "
                "Please try again later or re-upload a properly formatted resume."
            ) from e
        except Exception as e:
            await self._update_resume_status(resume_id, "failed")
            logger.error(
                "Unexpected error during extraction for resume %s: %s",
                resume_id,
                str(e),
            )
            raise ResumeParserError(
                "An unexpected error occurred during extraction. "
                "Please try re-uploading a properly formatted resume."
            ) from e

        # Store extracted data in database
        await self._store_extraction_result(
            resume_id, result["extracted_data"], result["confidence"]
        )

        return result

    def _get_resume_record(self, resume_id: str, user_id: str) -> dict:
        """Fetch resume record and verify ownership.

        Args:
            resume_id: The resume record ID.
            user_id: The authenticated user's ID.

        Returns:
            Resume record dictionary.

        Raises:
            ResumeParserError: If resume not found or access denied.
        """
        try:
            response = (
                self._client.table("resumes")
                .select("*")
                .eq("id", resume_id)
                .eq("user_id", user_id)
                .execute()
            )

            if not response.data:
                raise ResumeParserError("Resume not found or access denied.")

            return response.data[0]

        except ResumeParserError:
            raise
        except Exception as e:
            logger.error("Failed to fetch resume record %s: %s", resume_id, str(e))
            raise ResumeParserError("Failed to retrieve resume record.") from e

    def _download_file(self, file_path: str) -> bytes:
        """Download file from Supabase Storage.

        Args:
            file_path: Storage path of the file.

        Returns:
            Raw file content bytes.

        Raises:
            ResumeParserError: If download fails.
        """
        try:
            response = self._client.storage.from_("resumes").download(file_path)
            return response

        except Exception as e:
            logger.error("Failed to download file %s: %s", file_path, str(e))
            raise ResumeParserError(
                "Failed to download the resume file. Please try re-uploading."
            ) from e

    async def _update_resume_status(self, resume_id: str, status: str) -> None:
        """Update the extraction status of a resume record.

        Args:
            resume_id: The resume record ID.
            status: New status (processing, completed, failed).
        """
        try:
            self._client.table("resumes").update(
                {"extraction_status": status}
            ).eq("id", resume_id).execute()
        except Exception as e:
            logger.warning(
                "Failed to update resume status for %s to %s: %s",
                resume_id,
                status,
                str(e),
            )

    async def _store_extraction_result(
        self, resume_id: str, extracted_data: dict, confidence: float
    ) -> None:
        """Store extraction results in the database.

        Args:
            resume_id: The resume record ID.
            extracted_data: Structured extracted data.
            confidence: Confidence score (0.0-1.0).
        """
        try:
            self._client.table("resumes").update(
                {
                    "extracted_data": extracted_data,
                    "extraction_confidence": confidence,
                    "extraction_status": "completed",
                }
            ).eq("id", resume_id).execute()
        except Exception as e:
            logger.error(
                "Failed to store extraction result for resume %s: %s",
                resume_id,
                str(e),
            )
            raise ResumeParserError(
                "Failed to save extraction results."
            ) from e


def get_resume_parser() -> ResumeParser:
    """Factory function for ResumeParser dependency injection."""
    return ResumeParser()
