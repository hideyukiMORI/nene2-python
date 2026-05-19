"""Comment HTTP handlers — thin layer: parse → use-case → response.

Routes are nested under /notes/{note_id}/comments.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from nene2.http import PaginationQueryParser, PaginationResponse
from nene2.validation.exceptions import ValidationError, ValidationException

from .entity import Comment
from .use_case import (
    CreateCommentInput,
    CreateCommentUseCase,
    DeleteCommentInput,
    DeleteCommentUseCase,
    GetCommentUseCase,
    ListCommentsInput,
    ListCommentsUseCase,
    UpdateCommentInput,
    UpdateCommentUseCase,
)


class CreateCommentBody(BaseModel):
    body: str


class UpdateCommentBody(BaseModel):
    body: str


def _comment_dict(comment: Comment) -> dict[str, object]:
    return {"id": comment.id, "note_id": comment.note_id, "body": comment.body}


def make_comment_router(
    list_use_case: ListCommentsUseCase,
    get_use_case: GetCommentUseCase,
    create_use_case: CreateCommentUseCase,
    update_use_case: UpdateCommentUseCase,
    delete_use_case: DeleteCommentUseCase,
) -> APIRouter:
    router = APIRouter(prefix="/notes/{note_id}/comments", tags=["comments"])

    @router.get("")
    async def list_comments(note_id: int, request: Request) -> JSONResponse:
        pagination = PaginationQueryParser.parse(request)
        output = list_use_case.execute(
            ListCommentsInput(note_id=note_id, limit=pagination.limit, offset=pagination.offset)
        )
        return JSONResponse(
            PaginationResponse(
                items=[_comment_dict(c) for c in output.items],
                limit=output.limit,
                offset=output.offset,
                total=output.total,
            ).to_dict()
        )

    @router.get("/{comment_id}")
    async def get_comment(note_id: int, comment_id: int) -> JSONResponse:
        comment = get_use_case.execute(comment_id)
        return JSONResponse(_comment_dict(comment))

    @router.post("", status_code=201)
    async def create_comment(note_id: int, body: CreateCommentBody) -> JSONResponse:
        errors: list[ValidationError] = []
        if not body.body.strip():
            errors.append(ValidationError("body", "Body must not be empty.", "required"))
        if errors:
            raise ValidationException(errors)
        comment = create_use_case.execute(CreateCommentInput(note_id=note_id, body=body.body))
        return JSONResponse(_comment_dict(comment), status_code=201)

    @router.put("/{comment_id}")
    async def update_comment(
        note_id: int, comment_id: int, body: UpdateCommentBody
    ) -> JSONResponse:
        errors: list[ValidationError] = []
        if not body.body.strip():
            errors.append(ValidationError("body", "Body must not be empty.", "required"))
        if errors:
            raise ValidationException(errors)
        comment = update_use_case.execute(UpdateCommentInput(comment_id=comment_id, body=body.body))
        return JSONResponse(_comment_dict(comment))

    @router.delete("/{comment_id}", status_code=204)
    async def delete_comment(note_id: int, comment_id: int) -> None:
        delete_use_case.execute(DeleteCommentInput(comment_id=comment_id))

    return router
