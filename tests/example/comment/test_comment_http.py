"""HTTP integration tests for Comment endpoints."""

from fastapi.testclient import TestClient


def test_list_comments_empty(client: TestClient) -> None:
    response = client.get("/notes/1/comments")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_create_and_list_comments(client: TestClient) -> None:
    create_response = client.post("/notes/1/comments", json={"body": "first comment"})
    assert create_response.status_code == 201
    data = create_response.json()
    assert data["note_id"] == 1
    assert data["body"] == "first comment"

    list_response = client.get("/notes/1/comments")
    assert list_response.json()["total"] == 1


def test_get_comment(client: TestClient) -> None:
    created = client.post("/notes/1/comments", json={"body": "get me"}).json()
    response = client.get(f"/notes/1/comments/{created['id']}")
    assert response.status_code == 200
    assert response.json()["body"] == "get me"


def test_get_comment_not_found(client: TestClient) -> None:
    response = client.get("/notes/1/comments/9999")
    assert response.status_code == 404


def test_update_comment(client: TestClient) -> None:
    created = client.post("/notes/1/comments", json={"body": "original"}).json()
    response = client.put(f"/notes/1/comments/{created['id']}", json={"body": "updated"})
    assert response.status_code == 200
    assert response.json()["body"] == "updated"


def test_delete_comment(client: TestClient) -> None:
    created = client.post("/notes/1/comments", json={"body": "to delete"}).json()
    delete_response = client.delete(f"/notes/1/comments/{created['id']}")
    assert delete_response.status_code == 204
    get_response = client.get(f"/notes/1/comments/{created['id']}")
    assert get_response.status_code == 404


def test_create_comment_empty_body_returns_422(client: TestClient) -> None:
    response = client.post("/notes/1/comments", json={"body": "  "})
    assert response.status_code == 422
