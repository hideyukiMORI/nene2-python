"""Note HTTP handlers — thin layer: parse → use-case → response."""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from nene2.http import PaginationQueryParser
from nene2.validation.exceptions import ValidationError, ValidationException

from .use_case import (
    CreateNoteInput,
    CreateNoteUseCase,
    DeleteNoteInput,
    DeleteNoteUseCase,
    GetNoteInput,
    GetNoteUseCase,
    ListNotesInput,
    ListNotesUseCase,
    UpdateNoteInput,
    UpdateNoteUseCase,
)


class CreateNoteBody(BaseModel):
    title: str = Field(max_length=500, description="Note title.")
    body: str = Field(max_length=10_000, description="Note body.")


class UpdateNoteBody(BaseModel):
    title: str = Field(max_length=500, description="Note title.")
    body: str = Field(max_length=10_000, description="Note body.")


class NoteResponse(BaseModel):
    id: int = Field(description="Note identifier.")
    title: str = Field(description="Note title.")
    body: str = Field(description="Note body.")


class NoteListResponse(BaseModel):
    items: list[NoteResponse] = Field(description="Notes on this page.")
    limit: int = Field(description="Page size.")
    offset: int = Field(description="Page offset.")
    total: int = Field(description="Total number of notes.")


def _validate_note_body(title: str, body: str) -> None:
    errors: list[ValidationError] = []
    if not title.strip():
        errors.append(ValidationError("title", "Title must not be empty.", "required"))
    if not body.strip():
        errors.append(ValidationError("body", "Body must not be empty.", "required"))
    if errors:
        raise ValidationException(errors)


def make_note_router(
    list_use_case: ListNotesUseCase,
    get_use_case: GetNoteUseCase,
    create_use_case: CreateNoteUseCase,
    update_use_case: UpdateNoteUseCase,
    delete_use_case: DeleteNoteUseCase,
) -> APIRouter:
    router = APIRouter(prefix="/notes", tags=["notes"])

    @router.get("", response_model=NoteListResponse, summary="List notes")
    async def list_notes(request: Request) -> NoteListResponse:
        pagination = PaginationQueryParser.parse(request)
        output = list_use_case.execute(ListNotesInput(pagination.limit, pagination.offset))
        return NoteListResponse(
            items=[NoteResponse(id=n.id, title=n.title, body=n.body) for n in output.items],
            limit=output.limit,
            offset=output.offset,
            total=output.total,
        )

    @router.get("/{note_id}", response_model=NoteResponse, summary="Get a note")
    async def get_note(note_id: int) -> NoteResponse:
        note = get_use_case.execute(GetNoteInput(note_id))
        return NoteResponse(id=note.id, title=note.title, body=note.body)

    @router.post("", status_code=201, response_model=NoteResponse, summary="Create a note")
    async def create_note(body: CreateNoteBody) -> NoteResponse:
        _validate_note_body(body.title, body.body)
        note = create_use_case.execute(CreateNoteInput(body.title, body.body))
        return NoteResponse(id=note.id, title=note.title, body=note.body)

    @router.put("/{note_id}", response_model=NoteResponse, summary="Update a note")
    async def update_note(note_id: int, body: UpdateNoteBody) -> NoteResponse:
        _validate_note_body(body.title, body.body)
        note = update_use_case.execute(UpdateNoteInput(note_id, body.title, body.body))
        return NoteResponse(id=note.id, title=note.title, body=note.body)

    @router.delete("/{note_id}", status_code=204, summary="Delete a note")
    async def delete_note(note_id: int) -> None:
        delete_use_case.execute(DeleteNoteInput(note_id))

    return router
