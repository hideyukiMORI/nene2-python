"""Tests for AppSettings."""

import pytest
from pydantic import ValidationError

from nene2.config import AppSettings


def test_default_log_level_is_info() -> None:
    settings = AppSettings()
    assert settings.log_level == "INFO"


def test_log_level_is_normalized_to_uppercase() -> None:
    settings = AppSettings(log_level="debug")
    assert settings.log_level == "DEBUG"


def test_log_level_accepts_all_standard_levels() -> None:
    for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        settings = AppSettings(log_level=level)
        assert settings.log_level == level


def test_invalid_log_level_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        AppSettings(log_level="TRACE")


def test_default_app_env_is_local() -> None:
    settings = AppSettings()
    assert settings.app_env == "local"


def test_invalid_app_env_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        AppSettings(app_env="staging")


def test_db_url_sqlite_by_default() -> None:
    settings = AppSettings()
    assert settings.db_url.startswith("sqlite:///")


def test_db_url_mysql_format() -> None:
    settings = AppSettings(
        db_adapter="mysql",
        db_user="root",
        db_name="mydb",
        db_host="localhost",
        db_port=3306,
    )
    assert "mysql+pymysql://" in settings.db_url
    assert "mydb" in settings.db_url
