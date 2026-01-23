from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    MISTRAL_API_KEY: str
    REDIS_URL: str | None = None
    API_KEY_SALT: str = "default_salt"

    class Config:
        env_file = ".env"

settings = Settings()
