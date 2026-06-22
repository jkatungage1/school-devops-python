"""Configuration for the Courses service (Service B)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite database URL for this service.
    database_url: str = "sqlite:///./courses.db"


settings = Settings()
