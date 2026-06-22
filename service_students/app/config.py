"""Configuration for the Students service.

Settings are read from environment variables (with sensible defaults) using
pydantic-settings. The most important one is ``COURSES_SERVICE_URL`` which is
the base URL of Service B (the Courses service). In docker-compose this is set
to ``http://courses:8002``; locally it defaults to ``http://localhost:8002``.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Base URL of Service B (Courses). Overridden in docker-compose.
    courses_service_url: str = "http://localhost:8002"

    # SQLite database URL for this service.
    database_url: str = "sqlite:///./students.db"

    # Timeout (seconds) for outbound HTTP calls to Service B.
    http_timeout: float = 5.0


settings = Settings()
