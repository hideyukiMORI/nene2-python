"""Validation exceptions.

Equivalent to PHP Nene2\\Validation\\ValidationException and ValidationError.
Raised by handlers or use-cases to produce a 422 validation-failed Problem Details response.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidationError:
    """A single field-level validation failure.

    Args:
        field:   The input field that failed (e.g. ``"email"``).
        message: Human-readable description shown to the user
                 (e.g. ``"メールアドレスの形式が正しくありません"``).
        code:    Machine-readable identifier used by API clients to handle
                 specific errors programmatically (e.g. ``"invalid_email"``).
                 Must not contain spaces; use ``snake_case``.

    Example::

        ValidationError(
            field="email",
            message="メールアドレスの形式が正しくありません",
            code="invalid_email",
        )
    """

    field: str
    message: str
    code: str

    def __post_init__(self) -> None:
        for attr in ("field", "message", "code"):
            if not getattr(self, attr):
                raise ValueError(f"ValidationError.{attr} must not be empty")
        if " " in self.code:
            raise ValueError(
                f"ValidationError.code must not contain spaces (got {self.code!r}). "
                "Use snake_case, e.g. 'invalid_email'."
            )

    def to_dict(self) -> dict[str, str]:
        return {"field": self.field, "message": self.message, "code": self.code}


class ValidationException(Exception):
    """Raised when one or more validation rules fail.

    ErrorHandlerMiddleware maps this to a 422 validation-failed Problem Details response.

    For a single error, use the convenience method::

        raise ValidationException.single(
            field="email",
            message="メールアドレスの形式が正しくありません",
            code="invalid_email",
        )

    For multiple errors accumulated during validation::

        errors: list[ValidationError] = []
        if "@" not in email:
            errors.append(
                ValidationError(
                    field="email",
                    message="メールアドレスの形式が正しくありません",
                    code="invalid_email",
                )
            )
        if age < 18:
            errors.append(
                ValidationError(
                    field="age",
                    message="18歳以上である必要があります",
                    code="too_young",
                )
            )
        if errors:
            raise ValidationException(errors)

    Note: ``message`` is a human-readable string; ``code`` is a machine-readable
    ``snake_case`` identifier (e.g. ``"invalid_email"``, not ``"Invalid email"``).
    """

    def __init__(self, errors: list[ValidationError]) -> None:
        super().__init__("Validation failed")
        self.errors = errors

    @classmethod
    def single(cls, field: str, message: str, code: str) -> "ValidationException":
        """Convenience constructor for a single validation error.

        Args:
            field:   The input field that failed (e.g. ``"email"``).
            message: Human-readable description (e.g. ``"Invalid email address"``).
            code:    Machine-readable ``snake_case`` identifier (e.g. ``"invalid_email"``).
        """
        return cls([ValidationError(field, message, code)])
