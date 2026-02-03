import os
import secrets
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator


class Settings(BaseSettings):
    """
    Application settings with environment-aware configuration.
    
    SECURITY NOTES:
    - API_KEY_SALT is auto-generated if not provided (but should be set in production)
    - SMTP defaults are clearly marked as placeholders
    - Production mode enforces stricter validation
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
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # LLM Providers
    MISTRAL_API_KEY: str | None = None
    CHUTES_API_KEY: str | None = None
    CHUTES_BASE_URL: str = "https://llm.chutes.ai/v1"
    LLM_PROVIDER: str = "mistral"
    CHUTES_MODEL: str = "chutesai/Mistral-Small-3.1-24B-Instruct-2503"
    
    # Redis (for caching and rate limiting)
    REDIS_URL: str | None = None
    
    # Security - MUST be set in production
    API_KEY_SALT: str | None = None
    
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
    
    @property
    def api_key_salt_value(self) -> str:
        """Returns API key salt, generating one if not set (with warning)."""
        if self.API_KEY_SALT:
            return self.API_KEY_SALT
        # Generate a random salt if not provided (not ideal for production)
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
    
    if settings.SMTP_HOST == "smtp.example.com":
        warnings.warn("SMTP_HOST is using default placeholder in production!", UserWarning)
    
    if not settings.API_KEY_SALT:
        warnings.warn("API_KEY_SALT should be explicitly set in production!", UserWarning)
    
    if not settings.REDIS_URL:
        warnings.warn("REDIS_URL not set - rate limiting will use in-memory storage!", UserWarning)
