"""Comment domain exceptions and their HTTP handlers."""

from starlette.responses import Response

from nene2.http.problem_details import problem_details_response
from nene2.middleware.domain_exception import DomainExceptionHandlerProtocol


class CommentNotFoundException(Exception):
    def __init__(self, comment_id: int) -> None:
        self.comment_id = comment_id
        super().__init__(f"Comment {comment_id} not found.")


class CommentNotFoundExceptionHandler:
    def handles(self, exc: Exception) -> bool:
        return isinstance(exc, CommentNotFoundException)

    def handle(self, exc: Exception) -> Response:
        return problem_details_response("not-found", "Not Found", 404)


_: DomainExceptionHandlerProtocol = CommentNotFoundExceptionHandler()
