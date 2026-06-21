import os
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .api.v1 import agents, flows, settings
from .auth.jwt_auth import require_jwt
from .utils.logger import setup_logger

logger = setup_logger("crewai-agents")

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")
if IS_PRODUCTION:
    if CORS_ORIGINS == ["http://localhost:3000", "http://127.0.0.1:3000"]:
        logger.warning("CORS_ORIGINS not set for production! Using restrictive default.")
        CORS_ORIGINS = []

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="SimplifyEU CrewAI Agents",
    description=(
        "Microservice for AI-powered virtual accounting assistants. "
        "Provides financial reconciliation, tax compliance, document management, "
        "client communications, and weekly operational briefings."
    ),
    version="1.0.0",
    docs_url="/docs" if not IS_PRODUCTION else None,
    redoc_url="/redoc" if not IS_PRODUCTION else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-API-Key",
        "X-Account-ID",
        "X-User-ID",
    ],
)

# Register API routers.
# require_jwt enforces the Better Auth Bearer JWT on every /v1 route (with a
# dev/test-key bypass in non-production); get_current_account inside each route
# still provides the account/tenant scope.
app.include_router(
    agents.router, prefix="/v1", tags=["agents"], dependencies=[Depends(require_jwt)]
)
app.include_router(
    flows.router, prefix="/v1", tags=["flows"], dependencies=[Depends(require_jwt)]
)
app.include_router(
    settings.router, prefix="/v1", tags=["settings"], dependencies=[Depends(require_jwt)]
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "crewai-agents",
        "environment": ENVIRONMENT,
    }


@app.get("/security-info")
def security_info():
    return {
        "cors_origins_configured": len(CORS_ORIGINS),
        "is_production": IS_PRODUCTION,
        "rate_limiting_enabled": True,
        "docs_enabled": not IS_PRODUCTION,
    }
