"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.error_handler import register_exception_handlers
from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.history import router as history_router
from app.api.routes.interview import router as interview_router
from app.api.routes.presentation import router as presentation_router
from app.api.routes.profile import router as profile_router
from app.api.routes.resume import router as resume_router
from app.api.routes.sessions import router as sessions_router
from app.config import get_settings

# Configure logging for development visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# API version prefix used by all backend endpoints
API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    logger = logging.getLogger(__name__)
    settings = get_settings()
    logger.info(
        "JWT_SECRET loaded: length=%d, starts_with='%s'",
        len(settings.jwt_secret),
        settings.jwt_secret[:4] if settings.jwt_secret else "EMPTY",
    )

    # Validate URL formats (fail startup on invalid)
    try:
        resolved_frontend = settings.get_resolved_frontend_url()
    except ValueError as e:
        logger.error("Invalid FRONTEND_URL configuration: %s", e)
        raise SystemExit(1)

    try:
        resolved_backend = settings.get_resolved_backend_url()
    except ValueError as e:
        logger.error("Invalid BACKEND_URL configuration: %s", e)
        raise SystemExit(1)

    # Log warnings for missing optional vars
    default_frontend = "http://localhost:5173"
    default_backend = "http://localhost:8000"

    frontend_is_default = (
        not settings.frontend_url.strip()
        or settings.frontend_url.strip() == default_frontend
    )
    backend_is_default = (
        not settings.backend_url.strip()
        or settings.backend_url.strip() == default_backend
    )
    app_domain_missing = not settings.app_domain.strip()

    if frontend_is_default and settings.frontend_url.strip() != default_frontend:
        logger.warning(
            "FRONTEND_URL not set, using fallback: %s", default_frontend
        )
    elif not settings.frontend_url.strip():
        logger.warning(
            "FRONTEND_URL not set, using fallback: %s", default_frontend
        )

    if backend_is_default and settings.backend_url.strip() != default_backend:
        logger.warning(
            "BACKEND_URL not set, using fallback: %s", default_backend
        )
    elif not settings.backend_url.strip():
        logger.warning(
            "BACKEND_URL not set, using fallback: %s", default_backend
        )

    if app_domain_missing:
        logger.warning(
            "APP_DOMAIN not set, no custom domain configured"
        )

    # Log warning if APP_DOMAIN is set but FRONTEND_URL is not
    if not app_domain_missing and frontend_is_default:
        logger.warning(
            "APP_DOMAIN is configured but FRONTEND_URL is missing"
        )

    # Check if running in default-URL mode (no domain vars configured)
    if app_domain_missing and frontend_is_default and backend_is_default:
        logger.info("Running in default-URL mode")

    # Log SMTP status
    if settings.get_smtp_enabled():
        logger.info(
            "Email sending is active — host=%s, sender=%s",
            settings.smtp_host,
            settings.smtp_sender_email,
        )
    else:
        missing_vars = []
        if not settings.smtp_host:
            missing_vars.append("SMTP_HOST")
        if not settings.smtp_port or settings.smtp_port <= 0:
            missing_vars.append("SMTP_PORT")
        if not settings.smtp_sender_email:
            missing_vars.append("SMTP_SENDER_EMAIL")
        logger.warning(
            "Email features disabled — missing: %s", ", ".join(missing_vars)
        )

    # Log domain mode summary
    domain_mode = settings.get_domain_mode()
    logger.info("Domain mode: %s", domain_mode)

    yield
    # Shutdown


def create_app() -> FastAPI:
    """Application factory for creating the FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url=f"{API_V1_PREFIX}/docs",
        redoc_url=f"{API_V1_PREFIX}/redoc",
        openapi_url=f"{API_V1_PREFIX}/openapi.json",
        swagger_ui_init_oauth={},
    )

    # Add Bearer auth to OpenAPI schema so Swagger UI shows the Authorize button
    app.openapi_schema = None  # Reset to regenerate

    original_openapi = app.openapi

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = original_openapi()
        schema["components"] = schema.get("components", {})
        schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
        schema["security"] = [{"BearerAuth": []}]
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_parsed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register global exception handlers
    register_exception_handlers(app)

    # Core router with API v1 prefix
    v1_router = APIRouter(prefix=API_V1_PREFIX)

    # Health check endpoint
    @v1_router.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.app_version,
            "app_domain": settings.app_domain or "",
            "frontend_url": settings.get_resolved_frontend_url(),
            "backend_url": settings.get_resolved_backend_url(),
            "domain_mode": settings.get_domain_mode(),
        }

    # Include feature routers
    v1_router.include_router(analytics_router)
    v1_router.include_router(auth_router)
    v1_router.include_router(history_router)
    v1_router.include_router(interview_router)
    v1_router.include_router(presentation_router)
    v1_router.include_router(profile_router)
    v1_router.include_router(resume_router)
    v1_router.include_router(sessions_router)

    # Include the versioned router
    app.include_router(v1_router)

    return app


app = create_app()
