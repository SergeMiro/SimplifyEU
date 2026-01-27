from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    MISTRAL_API_KEY: str | None = None
    CHUTES_API_KEY: str | None = None
    LLM_PROVIDER: str = "mistral"
    CHUTES_MODEL: str = "glm-4.7"
    REDIS_URL: str | None = None
    API_KEY_SALT: str = "default_salt"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
