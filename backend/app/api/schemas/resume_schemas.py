"""Pydantic schemas for resume parsing and editing endpoints."""

from pydantic import BaseModel, Field


class ExtractedResumeData(BaseModel):
    """Schema for extracted resume data fields."""

    skills: list[str] = Field(default_factory=list, description="Extracted skills")
    projects: list[dict] = Field(
        default_factory=list,
        description="Extracted projects (name, description, technologies)",
    )
    experience: list[dict] = Field(
        default_factory=list,
        description="Extracted experience (title, company, duration, description)",
    )
    education: list[dict] = Field(
        default_factory=list,
        description="Extracted education (degree, institution, year)",
    )


class ResumeParseResponse(BaseModel):
    """Response schema for resume parse endpoint."""

    id: str
    extraction_status: str
    extracted_data: ExtractedResumeData | None = None
    extraction_confidence: float | None = None
    message: str | None = None


class ResumeExtractedResponse(BaseModel):
    """Response schema for getting extracted resume data."""

    id: str
    user_id: str
    file_name: str
    extracted_data: ExtractedResumeData | None = None
    extraction_confidence: float | None = None
    extraction_status: str
    user_confirmed: bool


class ResumeEditRequest(BaseModel):
    """Request schema for manually editing extracted resume data."""

    skills: list[str] | None = Field(default=None, description="Updated skills list")
    projects: list[dict] | None = Field(
        default=None, description="Updated projects list"
    )
    experience: list[dict] | None = Field(
        default=None, description="Updated experience list"
    )
    education: list[dict] | None = Field(
        default=None, description="Updated education list"
    )


class ResumeConfirmResponse(BaseModel):
    """Response schema for confirming extracted resume data."""

    id: str
    user_confirmed: bool
    message: str
