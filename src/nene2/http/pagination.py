"""Pagination helpers.

Equivalent to PHP Nene2\\Http\\PaginationQueryParser, PaginationQuery, PaginationResponse.
"""

from dataclasses import dataclass, field
from typing import Any

from fastapi import Request

from nene2.validation.exceptions import ValidationError, ValidationException


@dataclass(frozen=True)
class PaginationQuery:
    """Parsed and validated ?limit= / ?offset= parameters."""

    limit: int
    offset: int


class PaginationQueryParser:
    """Parses and validates pagination query parameters from a FastAPI Request."""

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
        limit = int(params.get("limit", default_limit))
        offset = int(params.get("offset", 0))

        errors: list[ValidationError] = []
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


@dataclass
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
        data: dict[str, Any] = {
            "items": self.items,
            "limit": self.limit,
            "offset": self.offset,
        }
        if self.total is not None:
            data["total"] = self.total
        return data
