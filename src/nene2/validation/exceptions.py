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
        for attr in ("field", "message", "code"):
            if not getattr(self, attr):
                raise ValueError(f"ValidationError.{attr} must not be empty")

    def to_dict(self) -> dict[str, str]:
        return {"field": self.field, "message": self.message, "code": self.code}


class ValidationException(Exception):
    """Raised when one or more validation rules fail.

    ErrorHandlerMiddleware maps this to a 422 validation-failed Problem Details response.

    For a single error, use the convenience method::

        raise ValidationException.single("email", "invalid", "invalid_email")

    For multiple errors accumulated during validation::

        errors = []
        if not valid_email:
            errors.append(ValidationError("email", "invalid", "invalid_email"))
        if errors:
            raise ValidationException(errors)
    """

    def __init__(self, errors: list[ValidationError]) -> None:
        super().__init__("Validation failed")
        self.errors = errors

    @classmethod
    def single(cls, field: str, message: str, code: str) -> "ValidationException":
        """Convenience constructor for a single validation error."""
        return cls([ValidationError(field, message, code)])
