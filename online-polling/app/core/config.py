from pydantic.v1 import BaseSettings, Field


class Settings(BaseSettings):
    DB_URL = Field(
        default="", description="configruation field for database url")
    ENV = Field(default="development",
                description="environment of the application like development, production, etc.")
    REDIS_URL = Field(default="redis://localhost:6379", description="Redis URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
