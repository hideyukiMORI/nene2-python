"""Note HTTP handlers — thin layer: parse → use-case → response."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from nene2.http import PaginationQueryParser, PaginationResponse
from nene2.validation.exceptions import ValidationError, ValidationException

from .use_case import (
    CreateNoteInput,
    CreateNoteUseCase,
    GetNoteUseCase,
    ListNotesInput,
    ListNotesUseCase,
)

router = APIRouter(prefix="/notes", tags=["notes"])


class CreateNoteBody(BaseModel):
    title: str
    body: str


def make_note_router(
    list_use_case: ListNotesUseCase,
    get_use_case: GetNoteUseCase,
    create_use_case: CreateNoteUseCase,
) -> APIRouter:
    @router.get("")
    async def list_notes(request: Request) -> JSONResponse:
        pagination = PaginationQueryParser.parse(request)
        output = list_use_case.execute(ListNotesInput(pagination.limit, pagination.offset))
        return JSONResponse(
            PaginationResponse(
                items=[{"id": n.id, "title": n.title, "body": n.body} for n in output.items],
                limit=output.limit,
                offset=output.offset,
                total=output.total,
            ).to_dict()
        )

    @router.get("/{note_id}")
    async def get_note(note_id: int) -> JSONResponse:
        note = get_use_case.execute(note_id)
        return JSONResponse({"id": note.id, "title": note.title, "body": note.body})

    @router.post("", status_code=201)
    async def create_note(body: CreateNoteBody) -> JSONResponse:
        errors: list[ValidationError] = []
        if not body.title.strip():
            errors.append(ValidationError("title", "Title must not be empty.", "required"))
        if errors:
            raise ValidationException(errors)

        note = create_use_case.execute(CreateNoteInput(body.title, body.body))
        return JSONResponse(
            {"id": note.id, "title": note.title, "body": note.body}, status_code=201
        )

    return router
