"""HTTP-level tests for the Note endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_list_notes_empty(client: TestClient) -> None:
    r = client.get("/examples/notes")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["total"] == 0


def test_create_and_get_note(client: TestClient) -> None:
    r = client.post("/examples/notes", json={"title": "Hello", "body": "World"})
    assert r.status_code == 201
    note_id = r.json()["id"]

    r2 = client.get(f"/examples/notes/{note_id}")
    assert r2.status_code == 200
    assert r2.json()["title"] == "Hello"


def test_create_note_empty_title_returns_422(client: TestClient) -> None:
    r = client.post("/examples/notes", json={"title": "", "body": "b"})
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "title"


def test_create_note_empty_title_and_body_returns_all_fields(client: TestClient) -> None:
    r = client.post("/examples/notes", json={"title": "", "body": ""})
    assert r.status_code == 422
    fields = {e["field"] for e in r.json()["errors"]}
    assert fields == {"title", "body"}


def test_get_nonexistent_note_returns_404(client: TestClient) -> None:
    r = client.get("/examples/notes/9999")
    assert r.status_code == 404


def test_update_note_returns_200(client: TestClient) -> None:
    r = client.post("/examples/notes", json={"title": "Old", "body": "Old body"})
    note_id = r.json()["id"]

    r2 = client.put(f"/examples/notes/{note_id}", json={"title": "New", "body": "New body"})
    assert r2.status_code == 200
    assert r2.json()["title"] == "New"
    assert r2.json()["body"] == "New body"


def test_update_nonexistent_note_returns_404(client: TestClient) -> None:
    r = client.put("/examples/notes/9999", json={"title": "T", "body": "B"})
    assert r.status_code == 404


def test_update_note_empty_title_returns_422(client: TestClient) -> None:
    r = client.post("/examples/notes", json={"title": "T", "body": "B"})
    note_id = r.json()["id"]
    r2 = client.put(f"/examples/notes/{note_id}", json={"title": "", "body": "B"})
    assert r2.status_code == 422


def test_delete_note_returns_204(client: TestClient) -> None:
    r = client.post("/examples/notes", json={"title": "T", "body": "B"})
    note_id = r.json()["id"]

    r2 = client.delete(f"/examples/notes/{note_id}")
    assert r2.status_code == 204

    r3 = client.get(f"/examples/notes/{note_id}")
    assert r3.status_code == 404


def test_delete_nonexistent_note_returns_404(client: TestClient) -> None:
    r = client.delete("/examples/notes/9999")
    assert r.status_code == 404


@pytest.mark.usefixtures("client")
def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "NENE2"
