"""Tests for PaginationQueryParser and PaginationResponse."""

from dataclasses import dataclass
from typing import Annotated
from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from nene2.http import PaginationDep, PaginationQueryParser, PaginationResponse
from nene2.validation.exceptions import ValidationException


def _make_app() -> FastAPI:
    app = FastAPI()

    @app.get("/items")
    async def items(request: Request) -> JSONResponse:
        pagination = PaginationQueryParser.parse(request)
        return JSONResponse({"limit": pagination.limit, "offset": pagination.offset})

    @app.get("/items-depends")
    async def items_depends(
        pagination: Annotated[PaginationQueryParser, Depends()],
    ) -> JSONResponse:
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
    mock_request = MagicMock(spec=Request)
    mock_request.query_params = {"limit": "0"}
    with pytest.raises(ValidationException) as exc_info:
        PaginationQueryParser.parse(mock_request)
    assert exc_info.value.errors[0].field == "limit"


def test_non_integer_limit_raises_validation_exception() -> None:
    mock_request = MagicMock(spec=Request)
    mock_request.query_params = {"limit": "abc"}
    with pytest.raises(ValidationException) as exc_info:
        PaginationQueryParser.parse(mock_request)
    assert exc_info.value.errors[0].field == "limit"
    assert exc_info.value.errors[0].code == "invalid"


def test_non_integer_offset_raises_validation_exception() -> None:
    mock_request = MagicMock(spec=Request)
    mock_request.query_params = {"offset": "xyz"}
    with pytest.raises(ValidationException) as exc_info:
        PaginationQueryParser.parse(mock_request)
    assert exc_info.value.errors[0].field == "offset"
    assert exc_info.value.errors[0].code == "invalid"


def test_both_invalid_collects_all_errors() -> None:
    mock_request = MagicMock(spec=Request)
    mock_request.query_params = {"limit": "abc", "offset": "xyz"}
    with pytest.raises(ValidationException) as exc_info:
        PaginationQueryParser.parse(mock_request)
    fields = [e.field for e in exc_info.value.errors]
    assert "limit" in fields
    assert "offset" in fields


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


def test_pagination_query_parser_as_depends_default() -> None:
    r = client.get("/items-depends")
    assert r.json() == {"limit": 20, "offset": 0}


def test_pagination_query_parser_as_depends_custom() -> None:
    r = client.get("/items-depends?limit=5&offset=10")
    assert r.json() == {"limit": 5, "offset": 10}


def test_pagination_query_parser_as_depends_out_of_range_returns_422() -> None:
    r = client.get("/items-depends?limit=0")
    assert r.status_code == 422


def test_pagination_response_to_dict_serializes_dataclass_items() -> None:
    @dataclass(frozen=True, slots=True)
    class Item:
        id: int
        name: str

    r = PaginationResponse(items=[Item(1, "foo"), Item(2, "bar")], limit=20, offset=0, total=2)
    data = r.to_dict()
    assert data["items"] == [{"id": 1, "name": "foo"}, {"id": 2, "name": "bar"}]


def test_pagination_response_to_dict_passes_through_dict_items() -> None:
    r = PaginationResponse(items=[{"id": 1}, {"id": 2}], limit=20, offset=0, total=2)
    assert r.to_dict()["items"] == [{"id": 1}, {"id": 2}]


def test_pagination_response_model_dump_is_alias_for_to_dict() -> None:
    """model_dump() は to_dict() の Pydantic 互換エイリアス。"""
    r = PaginationResponse(items=[{"id": 1}], limit=10, offset=0, total=1)
    assert r.model_dump() == r.to_dict()


def test_pagination_dep_type_alias_usable_in_handler() -> None:
    """PaginationDep 型エイリアスで Depends を省略して記述できる。"""
    test_app = FastAPI()

    @test_app.get("/things")
    def list_things(pagination: PaginationDep) -> JSONResponse:
        return JSONResponse({"limit": pagination.limit, "offset": pagination.offset})

    test_client = TestClient(test_app)
    r = test_client.get("/things?limit=5&offset=10")
    assert r.status_code == 200
    assert r.json()["limit"] == 5
    assert r.json()["offset"] == 10
