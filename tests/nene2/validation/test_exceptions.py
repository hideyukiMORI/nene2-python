"""Tests for ValidationError and ValidationException."""

import pytest

from nene2.validation.exceptions import ValidationError, ValidationException


def test_validation_error_to_dict() -> None:
    error = ValidationError(field="title", message="required", code="required")
    assert error.to_dict() == {"field": "title", "message": "required", "code": "required"}


def test_validation_error_rejects_empty_field() -> None:
    with pytest.raises(ValueError):
        ValidationError(field="", message="msg", code="code")


def test_validation_exception_stores_errors() -> None:
    errors = [ValidationError("f", "m", "c")]
    exc = ValidationException(errors)
    assert exc.errors == errors
    assert str(exc) == "Validation failed"


def test_validation_error_empty_field_message_names_the_field() -> None:
    with pytest.raises(ValueError, match="ValidationError.field must not be empty"):
        ValidationError(field="", message="msg", code="code")

    with pytest.raises(ValueError, match="ValidationError.message must not be empty"):
        ValidationError(field="f", message="", code="code")

    with pytest.raises(ValueError, match="ValidationError.code must not be empty"):
        ValidationError(field="f", message="msg", code="")


def test_validation_exception_single() -> None:
    exc = ValidationException.single("email", "invalid", "invalid_email")
    assert len(exc.errors) == 1
    assert exc.errors[0].field == "email"
    assert exc.errors[0].message == "invalid"
    assert exc.errors[0].code == "invalid_email"


def test_validation_exception_single_is_validation_exception() -> None:
    exc = ValidationException.single("f", "m", "c")
    assert isinstance(exc, ValidationException)


def test_validation_error_code_with_spaces_raises_value_error() -> None:
    with pytest.raises(ValueError, match="must not contain spaces"):
        ValidationError(field="email", message="Invalid email", code="invalid email")
