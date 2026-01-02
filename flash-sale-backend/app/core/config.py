from pydantic.v1 import BaseSettings, Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "Flash Sale Backend"
    PROJECT_VERSION: str = "1.0.0"
    PROJECT_DESCRIPTION: str = "backend api for flash sale like amazon, flipkart big billion days sale"
    DATABASE_URL = Field(default="postgresql+asyncpg://postgres:Admin123@localhost:5432/inventory_db", description="Database url")
    REDIS_URL: str = Field(default="redis://localhost:6379", description="Redis URL")
    ENV: str = Field(default="Development",
                     description="Environment in which this app runs")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
