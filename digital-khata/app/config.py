from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = Field(...)
    GROQ_API_KEY: str = Field(...)
    APP_HOST: str = Field(default="http://localhost:8000")
    SECRET_KEY: str = Field(...)
    DEBUG: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
