"""Typed application settings loaded from environment variables."""

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_debug: bool = False
    app_name: str = "nene2-python"
    security_headers_enabled: bool = True
    max_body_size: int = 1_048_576  # 1 MiB

    db_adapter: str = "sqlite"
    db_name: str = ":memory:"
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = ""
    db_password: SecretStr = SecretStr("")

    @field_validator("db_adapter")
    @classmethod
    def validate_adapter(cls, v: str) -> str:
        allowed = {"sqlite", "mysql", "pgsql"}
        if v not in allowed:
            raise ValueError(f"db_adapter must be one of {allowed}")
        return v

    @property
    def db_url(self) -> str:
        """Build a SQLAlchemy connection URL from adapter + credentials."""
        if self.db_adapter == "sqlite":
            return f"sqlite:///{self.db_name}"
        password = self.db_password.get_secret_value()
        port = self.db_port
        if self.db_adapter == "mysql":
            return f"mysql+pymysql://{self.db_user}:{password}@{self.db_host}:{port}/{self.db_name}"
        return f"postgresql+psycopg2://{self.db_user}:{password}@{self.db_host}:{port}/{self.db_name}"
