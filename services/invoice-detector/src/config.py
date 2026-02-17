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

    # ── Supabase ─────────────────────────────────
    SUPABASE_URL: str = "https://placeholder.supabase.co"
    SUPABASE_KEY: str = "placeholder-key"

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
    API_KEY_SALT: str = "invoice-detector-salt"

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
    if settings.SUPABASE_URL == "https://placeholder.supabase.co":
        raise ValueError("SUPABASE_URL must be set in production!")
    if settings.API_KEY_SALT == "invoice-detector-salt":
        import warnings
        warnings.warn("API_KEY_SALT uses default value in production!")
