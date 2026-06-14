from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    RAILRADAR_KEY: str
    RAPIDAPI_KEY: str
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/train_tracker"
    REDIS_URL: str = "redis://localhost:6379"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
