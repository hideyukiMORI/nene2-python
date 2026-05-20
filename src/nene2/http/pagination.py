"""Pagination helpers.

Equivalent to PHP Nene2\\Http\\PaginationQueryParser, PaginationQuery, PaginationResponse.
"""

import dataclasses
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import Depends, Query, Request

from nene2.validation.exceptions import ValidationError, ValidationException


@dataclass(frozen=True, slots=True)
class PaginationQuery:
    """Parsed and validated ?limit= / ?offset= parameters."""

    limit: int
    offset: int


class PaginationQueryParser:
    """Parses and validates pagination query parameters.

    Two usage patterns:

    **FastAPI Depends (recommended)**::

        from typing import Annotated
        from fastapi import Depends


        def list_items(pagination: Annotated[PaginationQueryParser, Depends()]) -> JSONResponse:
            result = use_case.execute(pagination.limit, pagination.offset)

    **Manual parse from Request (legacy)**::

        def list_items(request: Request) -> JSONResponse:
            pagination = PaginationQueryParser.parse(request)
            result = use_case.execute(pagination.limit, pagination.offset)
    """

    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=100, description="Items per page (1–100)")] = 20,
        offset: Annotated[int, Query(ge=0, description="Items to skip")] = 0,
    ) -> None:
        self.limit = limit
        self.offset = offset

    @staticmethod
    def parse(
        request: Request,
        *,
        default_limit: int = 20,
        max_limit: int = 100,
    ) -> PaginationQuery:
        """Parse ?limit= and ?offset= from the request.

        Raises ValidationException (→ 422) when values are out of range.
        """
        params = request.query_params

        errors: list[ValidationError] = []
        try:
            limit = int(params.get("limit", default_limit))
        except ValueError:
            errors.append(ValidationError("limit", "limit must be an integer.", "invalid"))
            limit = default_limit
        try:
            offset = int(params.get("offset", 0))
        except ValueError:
            errors.append(ValidationError("offset", "offset must be an integer.", "invalid"))
            offset = 0

        if limit < 1 or limit > max_limit:
            errors.append(
                ValidationError(
                    field="limit",
                    message=f"limit must be between 1 and {max_limit}.",
                    code="out_of_range",
                )
            )
        if offset < 0:
            errors.append(
                ValidationError(
                    field="offset",
                    message="offset must be 0 or greater.",
                    code="out_of_range",
                )
            )
        if errors:
            raise ValidationException(errors)

        return PaginationQuery(limit=limit, offset=offset)


@dataclass(frozen=True, slots=True)
class PaginationResponse:
    """Standard list-endpoint response envelope.

    Equivalent to PHP Nene2\\Http\\PaginationResponse.
    The ``total`` key is omitted from the output when not provided.
    """

    items: list[Any]
    limit: int
    offset: int
    total: int | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict.

        Items that are dataclass instances are converted via ``dataclasses.asdict()``
        so that ``JSONResponse(result.to_dict())`` works without extra steps.
        """
        data: dict[str, Any] = {
            "items": [
                dataclasses.asdict(item)
                if dataclasses.is_dataclass(item) and not isinstance(item, type)
                else item
                for item in self.items
            ],
            "limit": self.limit,
            "offset": self.offset,
        }
        if self.total is not None:
            data["total"] = self.total
        return data

    def model_dump(self) -> dict[str, Any]:
        """Alias for :meth:`to_dict` — Pydantic-compatible name for familiarity."""
        return self.to_dict()


type PaginationDep = Annotated[PaginationQueryParser, Depends(PaginationQueryParser)]
"""Type alias for injecting :class:`PaginationQueryParser` via ``Depends``.

Usage::

    from nene2.http import PaginationDep

    @app.get("/items")
    def list_items(pagination: PaginationDep) -> JSONResponse:
        items, total = use_case.execute(pagination.limit, pagination.offset)
        ...
"""
