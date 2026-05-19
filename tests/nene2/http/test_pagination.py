"""Tests for PaginationQueryParser and PaginationResponse."""

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.http import PaginationQueryParser, PaginationResponse
from nene2.validation.exceptions import ValidationException


def _make_app() -> FastAPI:
    app = FastAPI()

    @app.get("/items")
    async def items(request: Request) -> JSONResponse:
        pagination = PaginationQueryParser.parse(request)
        return JSONResponse({"limit": pagination.limit, "offset": pagination.offset})

    return app


client = TestClient(_make_app())


def test_default_pagination() -> None:
    r = client.get("/items")
    assert r.json() == {"limit": 20, "offset": 0}


def test_custom_pagination() -> None:
    r = client.get("/items?limit=10&offset=30")
    assert r.json() == {"limit": 10, "offset": 30}


def test_limit_out_of_range_raises() -> None:
    from unittest.mock import MagicMock

    from fastapi import Request as FastAPIRequest

    mock_request = MagicMock(spec=FastAPIRequest)
    mock_request.query_params = {"limit": "0"}
    with pytest.raises(ValidationException) as exc_info:
        PaginationQueryParser.parse(mock_request)
    assert exc_info.value.errors[0].field == "limit"


def test_pagination_response_without_total() -> None:
    r = PaginationResponse(items=[{"id": 1}], limit=20, offset=0)
    d = r.to_dict()
    assert d["limit"] == 20
    assert "total" not in d


def test_pagination_response_with_total() -> None:
    r = PaginationResponse(items=[], limit=10, offset=0, total=42)
    assert r.to_dict()["total"] == 42


def test_pagination_response_total_zero_is_included() -> None:
    r = PaginationResponse(items=[], limit=10, offset=0, total=0)
    assert r.to_dict()["total"] == 0
