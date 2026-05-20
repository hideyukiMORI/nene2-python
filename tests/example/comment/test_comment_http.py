"""HTTP integration tests for Comment endpoints."""

from collections.abc import Generator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from example.app import create_app
from nene2.config import AppSettings
from nene2.database import SqlAlchemyQueryExecutor


@contextmanager
def _make_client() -> Generator[TestClient, None, None]:
    app = create_app(AppSettings(throttle_enabled=False))
    yield TestClient(app)
    executor = getattr(app.state, "db_executor", None)
    if isinstance(executor, SqlAlchemyQueryExecutor):
        executor.engine.dispose()


def test_list_comments_empty() -> None:
    with _make_client() as client:
        note = client.post("/notes", json={"title": "Test Note", "body": "body"}).json()
        response = client.get(f"/notes/{note['id']}/comments")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert body["items"] == []


def test_create_and_list_comments() -> None:
    with _make_client() as client:
        note = client.post("/notes", json={"title": "Test Note", "body": "body"}).json()
        note_id = note["id"]
        create_response = client.post(f"/notes/{note_id}/comments", json={"body": "first comment"})
        assert create_response.status_code == 201
        data = create_response.json()
        assert data["note_id"] == note_id
        assert data["body"] == "first comment"

        list_response = client.get(f"/notes/{note_id}/comments")
        assert list_response.json()["total"] == 1


def test_get_comment() -> None:
    with _make_client() as client:
        note = client.post("/notes", json={"title": "Test Note", "body": "body"}).json()
        note_id = note["id"]
        created = client.post(f"/notes/{note_id}/comments", json={"body": "get me"}).json()
        response = client.get(f"/notes/{note_id}/comments/{created['id']}")
        assert response.status_code == 200
        assert response.json()["body"] == "get me"


def test_get_comment_not_found() -> None:
    with _make_client() as client:
        note = client.post("/notes", json={"title": "Test Note", "body": "body"}).json()
        response = client.get(f"/notes/{note['id']}/comments/9999")
        assert response.status_code == 404


def test_update_comment() -> None:
    with _make_client() as client:
        note = client.post("/notes", json={"title": "Test Note", "body": "body"}).json()
        note_id = note["id"]
        created = client.post(f"/notes/{note_id}/comments", json={"body": "original"}).json()
        url = f"/notes/{note_id}/comments/{created['id']}"
        response = client.put(url, json={"body": "updated"})
        assert response.status_code == 200
        assert response.json()["body"] == "updated"


def test_delete_comment() -> None:
    with _make_client() as client:
        note = client.post("/notes", json={"title": "Test Note", "body": "body"}).json()
        note_id = note["id"]
        created = client.post(f"/notes/{note_id}/comments", json={"body": "to delete"}).json()
        delete_response = client.delete(f"/notes/{note_id}/comments/{created['id']}")
        assert delete_response.status_code == 204
        get_response = client.get(f"/notes/{note_id}/comments/{created['id']}")
        assert get_response.status_code == 404


def test_create_comment_empty_body_returns_422() -> None:
    with _make_client() as client:
        note = client.post("/notes", json={"title": "Test Note", "body": "body"}).json()
        response = client.post(f"/notes/{note['id']}/comments", json={"body": "  "})
        assert response.status_code == 422


def test_create_comment_for_nonexistent_note_returns_404() -> None:
    with _make_client() as client:
        response = client.post("/notes/9999/comments", json={"body": "orphan"})
        assert response.status_code == 404


def test_get_comment_from_wrong_note_returns_404() -> None:
    with _make_client() as client:
        note1 = client.post("/notes", json={"title": "Note 1", "body": "b"}).json()
        note2 = client.post("/notes", json={"title": "Note 2", "body": "b"}).json()
        comment = client.post(
            f"/notes/{note1['id']}/comments", json={"body": "belongs to note1"}
        ).json()
        response = client.get(f"/notes/{note2['id']}/comments/{comment['id']}")
        assert response.status_code == 404


def test_list_comments_for_nonexistent_note_returns_404() -> None:
    with _make_client() as client:
        response = client.get("/notes/9999/comments")
        assert response.status_code == 404
