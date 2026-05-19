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
