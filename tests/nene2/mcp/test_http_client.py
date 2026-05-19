"""Tests for McpHttpResponse, McpHttpClientProtocol, and HttpxMcpClient."""

import json

import httpx
import pytest

from nene2.mcp import HttpxMcpClient, McpHttpClientProtocol, McpHttpError, McpHttpResponse


def _mock_transport(status: int, body: dict[str, object]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


def test_mcp_http_response_is_successful() -> None:
    assert McpHttpResponse(200, {}, "ok").is_successful() is True
    assert McpHttpResponse(201, {}, "").is_successful() is True
    assert McpHttpResponse(299, {}, "").is_successful() is True


def test_mcp_http_response_is_not_successful() -> None:
    assert McpHttpResponse(400, {}, "").is_successful() is False
    assert McpHttpResponse(404, {}, "").is_successful() is False
    assert McpHttpResponse(500, {}, "").is_successful() is False


def test_mcp_http_response_request_id() -> None:
    assert McpHttpResponse(200, {"x-request-id": "abc"}, "").request_id() == "abc"
    assert McpHttpResponse(200, {}, "").request_id() is None


def test_raise_for_error_does_nothing_on_success() -> None:
    McpHttpResponse(200, {}, "ok").raise_for_error()
    McpHttpResponse(204, {}, "").raise_for_error()


def test_raise_for_error_raises_on_4xx() -> None:
    with pytest.raises(McpHttpError) as exc_info:
        McpHttpResponse(404, {}, '{"detail":"not found"}').raise_for_error()
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.body


def test_raise_for_error_raises_on_5xx() -> None:
    with pytest.raises(McpHttpError):
        McpHttpResponse(500, {}, "server error").raise_for_error()


def test_mcp_http_error_message_includes_status_and_body() -> None:
    error = McpHttpError(404, "not found")
    assert "404" in str(error)
    assert "not found" in str(error)


def test_httpx_mcp_client_satisfies_protocol() -> None:
    assert isinstance(HttpxMcpClient(), McpHttpClientProtocol)


def test_has_authentication_without_token() -> None:
    assert HttpxMcpClient().has_authentication() is False


def test_has_authentication_with_token() -> None:
    assert HttpxMcpClient("my-token").has_authentication() is True


def test_get_request() -> None:
    transport = _mock_transport(200, {"id": 1, "title": "note"})
    client = HttpxMcpClient(transport=transport)
    response = client.get("http://test", "/notes/1")
    assert response.is_successful()
    assert json.loads(response.body)["id"] == 1


def test_post_request_sends_body() -> None:
    received: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        received.append(request.content)
        return httpx.Response(201, json={"id": 2})

    client = HttpxMcpClient(transport=httpx.MockTransport(handler))
    response = client.post("http://test", "/notes", {"title": "t", "body": "b"})
    assert response.status_code == 201
    assert b"title" in received[0]


def test_put_request() -> None:
    transport = _mock_transport(200, {"id": 1, "title": "updated"})
    client = HttpxMcpClient(transport=transport)
    response = client.put("http://test", "/notes/1", {"title": "updated", "body": "b"})
    assert response.is_successful()


def test_delete_request() -> None:
    transport = _mock_transport(204, {})
    client = HttpxMcpClient(transport=transport)
    response = client.delete("http://test", "/notes/1")
    assert response.status_code == 204


def test_bearer_token_added_to_header() -> None:
    received_headers: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        received_headers.append(dict(request.headers))
        return httpx.Response(200, json={})

    client = HttpxMcpClient("secret-token", transport=httpx.MockTransport(handler))
    client.get("http://test", "/notes")
    assert received_headers[0].get("authorization") == "Bearer secret-token"
