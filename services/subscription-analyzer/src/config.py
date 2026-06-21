from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment-aware configuration.

    SECURITY NOTES:
    - SERVICE_API_KEY must be set in production (shared key the web app sends).
    - SMTP defaults are clearly marked as placeholders.
    - Production mode enforces stricter validation.
    """
    model_config = ConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True,
    )

    # Environment
    ENVIRONMENT: str = "development"

    # CORS - comma-separated list of allowed origins
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Database (plain Postgres via SQLAlchemy + psycopg 3)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/simplifyeu_db"

    # Better Auth JWT verification (web app JWKS endpoint)
    BETTER_AUTH_JWKS_URL: str | None = None
    JWKS_CACHE_SECONDS: int = 300

    # Security - shared service key the web app sends in X-API-Key. MUST be set in production.
    SERVICE_API_KEY: str | None = None

    # Local file storage for uploaded statements and generated reports.
    UPLOAD_DIR: str = "/tmp/subscription-uploads"
    REPORTS_DIR: str = "/tmp/subscription-reports"

    # LLM Providers
    MISTRAL_API_KEY: str | None = None
    CHUTES_API_KEY: str | None = None
    CHUTES_BASE_URL: str = "https://llm.chutes.ai/v1"
    LLM_PROVIDER: str = "mistral"
    CHUTES_MODEL: str = "chutesai/Mistral-Small-3.1-24B-Instruct-2503"

    # Redis (for caching and rate limiting)
    REDIS_URL: str | None = None

    # SMTP Configuration for Email Reports
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "your_smtp_user@example.com"
    SMTP_PASSWORD: str = "your_smtp_password"
    SMTP_SENDER_EMAIL: str = "noreply@simplifyeu.com"
    SMTP_SENDER_NAME: str = "SimplifyEU Reports"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()

# Production safety checks
if settings.is_production:
    import warnings

    if settings.SMTP_HOST == "smtp.example.com":
        warnings.warn("SMTP_HOST is using default placeholder in production!", UserWarning)

    if not settings.SERVICE_API_KEY:
        warnings.warn("SERVICE_API_KEY not set in production!", UserWarning)

    if not settings.BETTER_AUTH_JWKS_URL:
        warnings.warn("BETTER_AUTH_JWKS_URL not set in production!", UserWarning)

    if not settings.REDIS_URL:
        warnings.warn("REDIS_URL not set - rate limiting will use in-memory storage!", UserWarning)
