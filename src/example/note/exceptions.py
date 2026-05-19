"""Note domain exceptions and their HTTP handlers."""

from starlette.responses import Response

from nene2.http.problem_details import problem_details_response


class NoteNotFoundException(Exception):
    def __init__(self, note_id: int) -> None:
        self.note_id = note_id
        super().__init__(f"Note {note_id} not found.")


class NoteNotFoundExceptionHandler:
    def handles(self, exc: Exception) -> bool:
        return isinstance(exc, NoteNotFoundException)

    def handle(self, exc: Exception) -> Response:
        return problem_details_response("not-found", "Not Found", 404)
