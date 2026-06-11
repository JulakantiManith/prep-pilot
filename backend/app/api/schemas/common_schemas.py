"""Common Pydantic schemas used across the API."""

from pydantic import BaseModel


class FieldError(BaseModel):
    """Represents a field-specific validation error."""

    field: str
    message: str
    type: str


class ErrorResponse(BaseModel):
    """Structured error response returned by the API.

    The detail field can be either a simple string message
    or a list of field-specific errors for validation failures.
    """

    detail: str | list[FieldError]
