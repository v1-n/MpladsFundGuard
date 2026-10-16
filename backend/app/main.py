from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from backend.app.core.config import settings
from backend.app.core.errors import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from backend.app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce startup token check: if auth is enabled, fail at startup if none are set
    if settings.AUDIT_AUTH_ENABLED and not settings.REVIEWER_TOKENS and not settings.IS_TESTING:
        raise RuntimeError(
            "CRITICAL STARTUP CONFIGURATION ERROR: AUDIT_AUTH_ENABLED is True but no reviewer tokens are configured. "
            "Set AUDIT_REVIEWER_TOKENS in your environment or .env file before starting the application."
        )
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    description="MPLADS FundGuard: Screening platform for public MPLADS procurement data irregularities and anomalies",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS - restricted to configured origins, credentials disabled for public API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Reviewer-Token"],
)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Health endpoint
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "version": "2.0.0",
        "disclaimer": settings.DISCLAIMER,
    }

# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)
