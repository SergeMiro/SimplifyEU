from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    MISTRAL_API_KEY: str | None = None
    CHUTES_API_KEY: str | None = None
    CHUTES_BASE_URL: str = "https://llm.chutes.ai/v1"
    LLM_PROVIDER: str = "mistral"
    CHUTES_MODEL: str = "chutesai/Mistral-Small-3.1-24B-Instruct-2503"
    REDIS_URL: str | None = None
    API_KEY_SALT: str = "default_salt"
    
    # SMTP Configuration for Email Reports
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "your_smtp_user@example.com"
    SMTP_PASSWORD: str = "your_smtp_password"
    SMTP_SENDER_EMAIL: str = "noreply@simplifyeu.com"
    SMTP_SENDER_NAME: str = "SimplifyEU Reports"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
