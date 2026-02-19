import os
import secrets
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """
    CrewAI Agents service configuration.

    SECURITY NOTES:
    - API_KEY_SALT is auto-generated if not provided (should be set in production)
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

    # Supabase
    SUPABASE_URL: str = "http://localhost:54321"
    SUPABASE_KEY: str = "test-key"

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

    # Security
    API_KEY_SALT: str | None = None

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
    def api_key_salt_value(self) -> str:
        if self.API_KEY_SALT:
            return self.API_KEY_SALT
        if self.is_production:
            import warnings
            warnings.warn(
                "API_KEY_SALT not set in production!",
                UserWarning,
            )
        return secrets.token_urlsafe(32)

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

    if not settings.API_KEY_SALT:
        warnings.warn("API_KEY_SALT should be explicitly set in production!", UserWarning)

    if not settings.whatsapp_configured:
        warnings.warn("WhatsApp/Twilio not configured — notifications disabled!", UserWarning)

    if not settings.smtp_configured:
        warnings.warn("SMTP not configured — email notifications disabled!", UserWarning)
