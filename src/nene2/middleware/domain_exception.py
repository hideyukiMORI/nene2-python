"""DomainExceptionHandlerProtocol — delegate domain errors to typed handlers."""

from typing import Protocol, runtime_checkable

from starlette.responses import Response


@runtime_checkable
class DomainExceptionHandlerProtocol(Protocol):
    """Map a domain exception to an HTTP response."""

    def handles(self, exc: Exception) -> bool:
        """Return True if this handler is responsible for *exc*."""
        ...

    def handle(self, exc: Exception) -> Response:
        """Convert *exc* to an HTTP response. Called only when handles() is True."""
        ...
