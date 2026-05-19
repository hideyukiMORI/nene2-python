"""HTTP-level tests for the Note endpoints."""

from fastapi.testclient import TestClient

from nene2.config import AppSettings
from src.example.app import create_app


def _client() -> TestClient:
    return TestClient(create_app(AppSettings()))


def test_list_notes_empty() -> None:
    r = _client().get("/notes")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["total"] == 0


def test_create_and_get_note() -> None:
    client = _client()
    r = client.post("/notes", json={"title": "Hello", "body": "World"})
    assert r.status_code == 201
    note_id = r.json()["id"]

    r2 = client.get(f"/notes/{note_id}")
    assert r2.status_code == 200
    assert r2.json()["title"] == "Hello"


def test_create_note_empty_title_returns_422() -> None:
    r = _client().post("/notes", json={"title": "", "body": "b"})
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "title"


def test_get_nonexistent_note_returns_404() -> None:
    r = _client().get("/notes/9999")
    assert r.status_code == 404


def test_health() -> None:
    r = _client().get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
