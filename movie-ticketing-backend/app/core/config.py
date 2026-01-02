from functools import lru_cache
from pydantic.v1 import BaseSettings, Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "Movie Ticketing API"
    PROJECT_VERSION: str = "0.1.0"
    PROJECT_DESCRIPTION: str = "API for movie ticketing system"
    ENV: str = Field(default="development", description="Environment of the application like development, production, etc.")
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:password@localhost:5432/movie_db", description="async Database URL")
    REDIS_URL: str = Field(default="redis://localhost:6379", description="Redis URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()


@lru_cache
def get_settings() -> Settings:
    return settings


   