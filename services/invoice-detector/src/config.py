"""
Pydantic Settings for Invoice Duplicate Detector.
"""
import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True,
    )

    # ── Environment ──────────────────────────────
    ENVIRONMENT: str = "development"

    # ── CORS ─────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ── Database (plain Postgres via SQLAlchemy + psycopg 3) ──
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/simplifyeu_db"

    # ── Better Auth JWT verification (web app JWKS endpoint) ──
    BETTER_AUTH_JWKS_URL: str | None = None
    JWKS_CACHE_SECONDS: int = 300

    # ── File Upload ──────────────────────────────
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = ".pdf,.png,.jpg,.jpeg,.tiff"
    UPLOAD_DIR: str = "/tmp/invoice-uploads"

    # ── OCR ──────────────────────────────────────
    OCR_ENABLED: bool = True
    OCR_LANGUAGE: str = "eng+fra"
    OCR_RETRY_MAX: int = 3
    OCR_RETRY_BACKOFF_BASE: float = 2.0

    # ── Fuzzy Matching Weights ───────────────────
    WEIGHT_INVOICE_NUMBER: float = 0.30
    WEIGHT_AMOUNT: float = 0.25
    WEIGHT_DATE: float = 0.15
    WEIGHT_VENDOR: float = 0.20
    WEIGHT_LINE_ITEMS: float = 0.10
    DUPLICATE_THRESHOLD: float = 0.85

    # ── Security ─────────────────────────────────
    # Shared service key the web app sends in X-API-Key.
    SERVICE_API_KEY: str | None = None

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [e.strip() for e in self.ALLOWED_EXTENSIONS.split(",") if e.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


settings = Settings()

# Production safety checks
if settings.is_production:
    import warnings

    if not settings.SERVICE_API_KEY:
        warnings.warn("SERVICE_API_KEY not set in production!", UserWarning)
    if not settings.BETTER_AUTH_JWKS_URL:
        warnings.warn("BETTER_AUTH_JWKS_URL not set in production!", UserWarning)
