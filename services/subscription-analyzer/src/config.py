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

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
