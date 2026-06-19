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
        allow_origins=settings.allowed_origins,
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
        }

    # Include feature routers
    v1_router.include_router(analytics_router)
    v1_router.include_router(auth_router)
    v1_router.include_router(history_router)
    v1_router.include_router(interview_router)
    v1_router.include_router(profile_router)
    v1_router.include_router(resume_router)
    v1_router.include_router(sessions_router)

    # Include the versioned router
    app.include_router(v1_router)

    return app


app = create_app()
