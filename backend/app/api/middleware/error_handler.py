"""Global exception handler middleware for structured error responses."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.schemas.common_schemas import ErrorResponse, FieldError

logger = logging.getLogger(__name__)


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTP exceptions and return structured ErrorResponse."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(detail=str(exc.detail)).model_dump(),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors with field-specific messages.

    Returns a 422 response with structured field errors per Requirement 17.5.
    """
    field_errors: list[FieldError] = []
    for error in exc.errors():
        # Extract field name from the location tuple (e.g., ("body", "email") -> "email")
        loc = error.get("loc", ())
        field_name = str(loc[-1]) if loc else "unknown"
        # Skip the first element if it's the request location type (body, query, path)
        if len(loc) > 1 and loc[0] in ("body", "query", "path", "header"):
            field_name = str(loc[-1])

        field_errors.append(
            FieldError(
                field=field_name,
                message=error.get("msg", "Validation error"),
                type=error.get("type", "value_error"),
            )
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(detail=[e.model_dump() for e in field_errors]).model_dump(),
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle all unhandled exceptions with a generic error message.

    Logs the full exception for debugging but returns a safe message to clients.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail="An internal server error occurred. Please try again later."
        ).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app instance."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
