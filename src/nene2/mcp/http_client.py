"""MCP HTTP client — equivalent to PHP LocalMcpHttpClientInterface.

Provides a lightweight HTTP transport for calling a nene2 API from MCP tool handlers.
The default implementation uses httpx; inject a custom McpHttpClientProtocol for tests.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import httpx
from httpx import BaseTransport


@dataclass(frozen=True, slots=True)
class McpHttpResponse:
    """HTTP response value object returned by McpHttpClientProtocol."""

    status_code: int
    headers: dict[str, str]
    body: str

    def is_successful(self) -> bool:
        return 200 <= self.status_code < 300

    def request_id(self) -> str | None:
        return self.headers.get("x-request-id")


@runtime_checkable
class McpHttpClientProtocol(Protocol):
    """Structural contract for MCP HTTP clients."""

    def get(self, base_url: str, path: str) -> McpHttpResponse: ...

    def post(
        self, base_url: str, path: str, body: dict[str, object]
    ) -> McpHttpResponse: ...

    def put(
        self, base_url: str, path: str, body: dict[str, object]
    ) -> McpHttpResponse: ...

    def delete(self, base_url: str, path: str) -> McpHttpResponse: ...

    def has_authentication(self) -> bool: ...


class HttpxMcpClient:
    """httpx-backed MCP HTTP client with optional Bearer token authentication.

    Pass a custom transport (e.g. httpx.MockTransport or httpx.WSGITransport)
    for testing without making real network calls.
    """

    def __init__(
        self,
        bearer_token: str | None = None,
        *,
        transport: BaseTransport | None = None,
    ) -> None:
        self._bearer_token = bearer_token
        self._transport = transport

    def get(self, base_url: str, path: str) -> McpHttpResponse:
        return self._request("GET", base_url, path, None)

    def post(
        self, base_url: str, path: str, body: dict[str, object]
    ) -> McpHttpResponse:
        return self._request("POST", base_url, path, body)

    def put(
        self, base_url: str, path: str, body: dict[str, object]
    ) -> McpHttpResponse:
        return self._request("PUT", base_url, path, body)

    def delete(self, base_url: str, path: str) -> McpHttpResponse:
        return self._request("DELETE", base_url, path, None)

    def has_authentication(self) -> bool:
        return self._bearer_token is not None

    def _request(
        self,
        method: str,
        base_url: str,
        path: str,
        body: dict[str, object] | None,
    ) -> McpHttpResponse:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._bearer_token is not None:
            headers["Authorization"] = f"Bearer {self._bearer_token}"

        with httpx.Client(transport=self._transport) as client:
            response = client.request(
                method,
                base_url.rstrip("/") + path,
                json=body,
                headers=headers,
            )
        return McpHttpResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.text,
        )
