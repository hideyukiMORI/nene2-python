"""Typed application settings loaded from environment variables."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_debug: bool = False
    app_name: str = "nene2-python"

    db_adapter: str = "sqlite"
    db_name: str = ":memory:"
    db_host: str = ""
    db_port: int = 0
    db_user: str = ""
    db_password: str = ""

    @field_validator("db_adapter")
    @classmethod
    def validate_adapter(cls, v: str) -> str:
        allowed = {"sqlite", "mysql", "pgsql"}
        if v not in allowed:
            raise ValueError(f"db_adapter must be one of {allowed}")
        return v
