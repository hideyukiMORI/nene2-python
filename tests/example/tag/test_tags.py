"""HTTP-level tests for the Tag endpoints."""

from fastapi.testclient import TestClient

from nene2.config import AppSettings
from src.example.app import create_app


def _client() -> TestClient:
    return TestClient(create_app(AppSettings()))


def test_list_tags_empty() -> None:
    r = _client().get("/tags")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_create_and_get_tag() -> None:
    client = _client()
    r = client.post("/tags", json={"name": "python"})
    assert r.status_code == 201
    tag_id = r.json()["id"]

    r2 = client.get(f"/tags/{tag_id}")
    assert r2.status_code == 200
    assert r2.json()["name"] == "python"


def test_create_tag_empty_name_returns_422() -> None:
    r = _client().post("/tags", json={"name": ""})
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "name"


def test_get_nonexistent_tag_returns_404() -> None:
    r = _client().get("/tags/9999")
    assert r.status_code == 404


def test_update_tag_returns_200() -> None:
    client = _client()
    r = client.post("/tags", json={"name": "old"})
    tag_id = r.json()["id"]

    r2 = client.put(f"/tags/{tag_id}", json={"name": "new"})
    assert r2.status_code == 200
    assert r2.json()["name"] == "new"


def test_update_nonexistent_tag_returns_404() -> None:
    r = _client().put("/tags/9999", json={"name": "x"})
    assert r.status_code == 404


def test_update_tag_empty_name_returns_422() -> None:
    client = _client()
    r = client.post("/tags", json={"name": "t"})
    tag_id = r.json()["id"]
    r2 = client.put(f"/tags/{tag_id}", json={"name": ""})
    assert r2.status_code == 422


def test_delete_tag_returns_204() -> None:
    client = _client()
    r = client.post("/tags", json={"name": "temp"})
    tag_id = r.json()["id"]

    r2 = client.delete(f"/tags/{tag_id}")
    assert r2.status_code == 204

    r3 = client.get(f"/tags/{tag_id}")
    assert r3.status_code == 404


def test_delete_nonexistent_tag_returns_404() -> None:
    r = _client().delete("/tags/9999")
    assert r.status_code == 404


def test_list_tags_pagination() -> None:
    client = _client()
    for name in ["a", "b", "c"]:
        client.post("/tags", json={"name": name})

    r = client.get("/tags?limit=2&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3
