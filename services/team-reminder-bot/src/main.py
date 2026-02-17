import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .api.v1 import reminders, teams
from .utils.logger import setup_logger

logger = setup_logger("team-reminder-bot")

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# CORS Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
if IS_PRODUCTION:
    if CORS_ORIGINS == ["http://localhost:3000", "http://127.0.0.1:3000"]:
        logger.warning("CORS_ORIGINS not set for production! Using restrictive default.")
        CORS_ORIGINS = []

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Team Reminder Bot",
    description="Intelligent reminder service with context-aware notifications for Slack/Teams.",
    version="1.0.0",
    docs_url="/docs" if not IS_PRODUCTION else None,
    redoc_url="/redoc" if not IS_PRODUCTION else None,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Account-ID", "X-User-ID"],
)

app.include_router(reminders.router, prefix="/v1", tags=["reminders"])
app.include_router(teams.router, prefix="/v1", tags=["teams"])


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "team-reminder-bot", "environment": ENVIRONMENT}


@app.get("/security-info")
def security_info():
    """Returns security configuration (non-sensitive) for debugging."""
    return {
        "cors_origins_configured": len(CORS_ORIGINS),
        "is_production": IS_PRODUCTION,
        "rate_limiting_enabled": True,
        "docs_enabled": not IS_PRODUCTION,
    }
