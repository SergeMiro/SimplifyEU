from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """
    CrewAI Agents service configuration.

    SECURITY NOTES:
    - SERVICE_API_KEY must be set in production (shared key the web app sends).
    - WhatsApp/Twilio credentials must be set for notification features
    - LLM API keys are required for agent intelligence
    """

    model_config = ConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True,
    )

    # Environment
    ENVIRONMENT: str = "development"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Database (plain Postgres via SQLAlchemy + psycopg 3)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/simplifyeu_db"

    # Better Auth JWT verification (web app JWKS endpoint)
    BETTER_AUTH_JWKS_URL: str | None = None
    JWKS_CACHE_SECONDS: int = 300

    # Security - shared service key the web app sends in X-API-Key. MUST be set in production.
    SERVICE_API_KEY: str | None = None

    # LLM Providers
    OPENAI_API_KEY: str | None = None
    MISTRAL_API_KEY: str | None = None
    CHUTES_API_KEY: str | None = None
    CHUTES_BASE_URL: str = "https://llm.chutes.ai/v1"
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"

    # WhatsApp / Twilio
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_WHATSAPP_FROM: str | None = None

    # SMTP for email notifications
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "your_smtp_user@example.com"
    SMTP_PASSWORD: str = "your_smtp_password"
    SMTP_SENDER_EMAIL: str = "noreply@simplifyeu.com"
    SMTP_SENDER_NAME: str = "SimplifyEU Agents"
    SMTP_USE_TLS: bool = True

    # Redis
    REDIS_URL: str | None = None

    # Agent defaults
    WEEKLY_REPORT_DAY: str = "monday"
    WEEKLY_REPORT_HOUR: int = 8
    TAX_REMINDER_DAYS_BEFORE: int = 5

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def whatsapp_configured(self) -> bool:
        return all([
            self.TWILIO_ACCOUNT_SID,
            self.TWILIO_AUTH_TOKEN,
            self.TWILIO_WHATSAPP_FROM,
        ])

    @property
    def smtp_configured(self) -> bool:
        return self.SMTP_HOST != "smtp.example.com"


settings = Settings()

if settings.is_production:
    import warnings

    if not settings.SERVICE_API_KEY:
        warnings.warn("SERVICE_API_KEY not set in production!", UserWarning)

    if not settings.BETTER_AUTH_JWKS_URL:
        warnings.warn("BETTER_AUTH_JWKS_URL not set in production!", UserWarning)

    if not settings.whatsapp_configured:
        warnings.warn("WhatsApp/Twilio not configured — notifications disabled!", UserWarning)

    if not settings.smtp_configured:
        warnings.warn("SMTP not configured — email notifications disabled!", UserWarning)
