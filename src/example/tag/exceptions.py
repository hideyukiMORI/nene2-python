"""Tag domain exceptions and their HTTP handlers."""

from starlette.responses import Response

from nene2.http.problem_details import problem_details_response


class TagNotFoundException(Exception):
    def __init__(self, tag_id: int) -> None:
        self.tag_id = tag_id
        super().__init__(f"Tag {tag_id} not found.")


class TagNotFoundExceptionHandler:
    def handles(self, exc: Exception) -> bool:
        return isinstance(exc, TagNotFoundException)

    def handle(self, exc: Exception) -> Response:
        return problem_details_response("not-found", "Not Found", 404)
