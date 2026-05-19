"""Smoke tests for scripts/export_openapi.py."""

import pathlib

import pytest
import yaml

from scripts.export_openapi import main


def test_main_writes_yaml_file(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()

    main()

    assert (tmp_path / "docs" / "openapi.yaml").exists()


def test_main_yaml_is_valid_openapi(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()

    main()

    content = yaml.safe_load((tmp_path / "docs" / "openapi.yaml").read_text())
    assert content["openapi"].startswith("3.")
    assert "/notes" in content["paths"]


def test_main_prints_output_path(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()

    main()

    assert "openapi.yaml" in capsys.readouterr().out
