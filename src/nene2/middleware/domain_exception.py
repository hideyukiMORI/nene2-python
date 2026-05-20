"""DomainExceptionHandlerProtocol — delegate domain errors to typed handlers."""

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from starlette.responses import Response

from nene2.http.problem_details import problem_details_response


@runtime_checkable
class DomainExceptionHandlerProtocol(Protocol):
    """Map a domain exception to an HTTP response."""

    def handles(self, exc: Exception) -> bool:
        """Return True if this handler is responsible for *exc*."""
        ...

    def handle(self, exc: Exception) -> Response:
        """Convert *exc* to an HTTP response. Called only when handles() is True."""
        ...


class SimpleDomainHandler:
    """Convenience handler that maps one exception class to a fixed Problem Details response.

    Eliminates the boilerplate of implementing ``handles()`` and ``handle()`` for
    simple cases where the entire response is determined by the exception type::

        from nene2.middleware import SimpleDomainHandler

        handlers = [
            SimpleDomainHandler(PostNotFoundError, "post-not-found", "Post Not Found", 404),
            SimpleDomainHandler(PostAccessDeniedError, "post-access-denied", "Access Denied", 403),
        ]
        app.add_middleware(ErrorHandlerMiddleware, domain_handlers=handlers)

    When you need a dynamic ``detail`` or extra fields derived from the exception,
    pass an ``extra_factory`` callable.  The dict returned by ``extra_factory`` is merged
    **at the top level** of the Problem Details response (RFC 9457 extension members) —
    the keys appear directly alongside ``type``, ``title``, etc., NOT nested under
    an ``"extra"`` key::

        SimpleDomainHandler(
            PostNotFoundError,
            "post-not-found",
            "Post Not Found",
            404,
            detail_factory=lambda exc: str(exc),
            extra_factory=lambda exc: {"post_id": exc.post_id},
        )
        # Response: {"type": "...", "status": 404, ..., "post_id": 123}
        #       NOT: {"type": "...", ..., "extra": {"post_id": 123}}
    """

    def __init__(
        self,
        exception_class: type[Exception],
        problem_type: str,
        title: str,
        status: int,
        detail: str | None = None,
        *,
        detail_factory: Callable[[Exception], str] | None = None,
        extra_factory: Callable[[Exception], dict[str, Any]] | None = None,
    ) -> None:
        self._exception_class = exception_class
        self._problem_type = problem_type
        self._title = title
        self._status = status
        self._detail = detail
        self._detail_factory = detail_factory
        self._extra_factory = extra_factory

    def handles(self, exc: Exception) -> bool:
        return isinstance(exc, self._exception_class)

    def handle(self, exc: Exception) -> Response:
        detail = self._detail_factory(exc) if self._detail_factory else self._detail
        extra = self._extra_factory(exc) if self._extra_factory else None
        return problem_details_response(
            self._problem_type,
            self._title,
            self._status,
            detail,
            extra,
        )
