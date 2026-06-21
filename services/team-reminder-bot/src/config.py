import os
import secrets
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """
    Team Reminder Bot settings with environment-aware configuration.

    SECURITY NOTES:
    - API_KEY_SALT is auto-generated if not provided (but should be set in production)
    - SLACK tokens must be set for Slack integration to work
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

    # Database (plain Postgres via SQLAlchemy)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/simplifyeu_db"

    # Better Auth JWT verification (web app JWKS endpoint, e.g. http://web/api/auth/jwks)
    BETTER_AUTH_JWKS_URL: str | None = None
    JWKS_CACHE_SECONDS: int = 300

    # Slack Configuration
    SLACK_BOT_TOKEN: str | None = None
    SLACK_SIGNING_SECRET: str | None = None
    SLACK_APP_TOKEN: str | None = None

    # Queue Configuration
    QUEUE_POLL_INTERVAL_SECONDS: int = 5
    QUEUE_MAX_RETRIES: int = 3

    # Reminder Defaults
    DEFAULT_SNOOZE_MINUTES: int = 15
    MAX_REMINDERS_PER_USER: int = 100

    # Security
    API_KEY_SALT: str | None = None
    # Shared service key the web app sends in X-API-Key.
    SERVICE_API_KEY: str | None = None

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def api_key_salt_value(self) -> str:
        """Returns API key salt, generating one if not set (with warning)."""
        if self.API_KEY_SALT:
            return self.API_KEY_SALT
        if self.is_production:
            import warnings
            warnings.warn(
                "API_KEY_SALT not set in production! This can cause issues with key validation.",
                UserWarning
            )
        return secrets.token_urlsafe(32)


settings = Settings()

# Production safety checks
if settings.is_production:
    import warnings

    if not settings.SLACK_BOT_TOKEN:
        warnings.warn("SLACK_BOT_TOKEN not set in production!", UserWarning)

    if not settings.API_KEY_SALT:
        warnings.warn("API_KEY_SALT should be explicitly set in production!", UserWarning)
