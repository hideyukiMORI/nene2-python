"""Tests for nene2.log.setup."""

import logging

from nene2.config import AppSettings
from nene2.log import setup_logging


def test_setup_logging_defaults_to_info_level() -> None:
    setup_logging()
    assert logging.getLogger().level == logging.INFO


def test_setup_logging_accepts_debug_level() -> None:
    setup_logging(log_level="DEBUG")
    assert logging.getLogger().level == logging.DEBUG


def test_setup_logging_accepts_warning_level() -> None:
    setup_logging(log_level="WARNING")
    assert logging.getLogger().level == logging.WARNING


def test_setup_logging_accepts_error_level() -> None:
    setup_logging(log_level="ERROR")
    assert logging.getLogger().level == logging.ERROR


def test_setup_logging_case_insensitive_level() -> None:
    setup_logging(log_level="debug")
    assert logging.getLogger().level == logging.DEBUG


def test_setup_logging_integrates_with_app_settings_log_level() -> None:
    settings = AppSettings(log_level="DEBUG")
    setup_logging(app_env=settings.app_env, log_level=settings.log_level)
    assert logging.getLogger().level == logging.DEBUG


def test_setup_logging_local_env_uses_console_renderer() -> None:
    setup_logging(app_env="local")
    root = logging.getLogger()
    assert len(root.handlers) == 1


def test_setup_logging_production_env_uses_json_renderer() -> None:
    setup_logging(app_env="production")
    root = logging.getLogger()
    assert len(root.handlers) == 1
