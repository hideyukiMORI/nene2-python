"""Validation exceptions.

Equivalent to PHP Nene2\\Validation\\ValidationException and ValidationError.
Raised by handlers or use-cases to produce a 422 validation-failed Problem Details response.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidationError:
    """A single field-level validation failure."""

    field: str
    message: str
    code: str

    def __post_init__(self) -> None:
        if not self.field or not self.message or not self.code:
            raise ValueError("field, message, and code must be non-empty strings")

    def to_dict(self) -> dict[str, str]:
        return {"field": self.field, "message": self.message, "code": self.code}


class ValidationException(Exception):
    """Raised when one or more validation rules fail.

    ErrorHandlerMiddleware maps this to a 422 validation-failed Problem Details response.
    """

    def __init__(self, errors: list[ValidationError]) -> None:
        super().__init__("Validation failed")
        self.errors = errors
