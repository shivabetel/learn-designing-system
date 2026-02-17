from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:Admin123@localhost:5432/wallet_db")
    APP_NAME: str = Field(default="Wallet Ledger")

    # class Config:
    #     env_file = ".env"
    #     env_file_encoding = "utf-8"
    # model_config = SettingsConfigDict(
    #     env_file=".env",
    #     env_file_encoding="utf-8"
    # )


settings = Settings()
