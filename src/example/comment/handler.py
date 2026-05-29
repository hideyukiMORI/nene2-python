"""Comment HTTP handlers — thin layer: parse → use-case → response.

Routes are nested under /notes/{note_id}/comments.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from nene2.http import PaginationQueryParser

from .exceptions import CommentNotFoundException
from .use_case import (
    MAX_COMMENT_BODY_LENGTH,
    CreateCommentInput,
    CreateCommentUseCase,
    DeleteCommentInput,
    DeleteCommentUseCase,
    GetCommentInput,
    GetCommentUseCase,
    ListCommentsInput,
    ListCommentsUseCase,
    UpdateCommentInput,
    UpdateCommentUseCase,
)


class CreateCommentBody(BaseModel):
    body: str = Field(max_length=MAX_COMMENT_BODY_LENGTH, description="Comment body.")


class UpdateCommentBody(BaseModel):
    body: str = Field(max_length=MAX_COMMENT_BODY_LENGTH, description="Comment body.")


class CommentResponse(BaseModel):
    id: int = Field(description="Comment identifier.")
    note_id: int = Field(description="Owning note identifier.")
    body: str = Field(description="Comment body.")


class CommentListResponse(BaseModel):
    items: list[CommentResponse] = Field(description="Comments on this page.")
    limit: int = Field(description="Page size.")
    offset: int = Field(description="Page offset.")
    total: int = Field(description="Total number of comments.")


def make_comment_router(
    list_use_case: ListCommentsUseCase,
    get_use_case: GetCommentUseCase,
    create_use_case: CreateCommentUseCase,
    update_use_case: UpdateCommentUseCase,
    delete_use_case: DeleteCommentUseCase,
) -> APIRouter:
    router = APIRouter(prefix="/notes/{note_id}/comments", tags=["comments"])

    @router.get("", response_model=CommentListResponse, summary="List comments")
    async def list_comments(note_id: int, request: Request) -> CommentListResponse:
        pagination = PaginationQueryParser.parse(request)
        output = list_use_case.execute(
            ListCommentsInput(note_id=note_id, limit=pagination.limit, offset=pagination.offset)
        )
        return CommentListResponse(
            items=[CommentResponse(id=c.id, note_id=c.note_id, body=c.body) for c in output.items],
            limit=output.limit,
            offset=output.offset,
            total=output.total,
        )

    @router.get("/{comment_id}", response_model=CommentResponse, summary="Get a comment")
    async def get_comment(note_id: int, comment_id: int) -> CommentResponse:
        comment = get_use_case.execute(GetCommentInput(comment_id=comment_id))
        if comment.note_id != note_id:
            raise CommentNotFoundException(comment_id)
        return CommentResponse(id=comment.id, note_id=comment.note_id, body=comment.body)

    @router.post("", status_code=201, response_model=CommentResponse, summary="Create a comment")
    async def create_comment(note_id: int, body: CreateCommentBody) -> CommentResponse:
        comment = create_use_case.execute(CreateCommentInput(note_id=note_id, body=body.body))
        return CommentResponse(id=comment.id, note_id=comment.note_id, body=comment.body)

    @router.put("/{comment_id}", response_model=CommentResponse, summary="Update a comment")
    async def update_comment(
        note_id: int, comment_id: int, body: UpdateCommentBody
    ) -> CommentResponse:
        update_input = UpdateCommentInput(comment_id=comment_id, body=body.body)
        existing = get_use_case.execute(GetCommentInput(comment_id=comment_id))
        if existing.note_id != note_id:
            raise CommentNotFoundException(comment_id)
        comment = update_use_case.execute(update_input)
        return CommentResponse(id=comment.id, note_id=comment.note_id, body=comment.body)

    @router.delete("/{comment_id}", status_code=204, summary="Delete a comment")
    async def delete_comment(note_id: int, comment_id: int) -> None:
        existing = get_use_case.execute(GetCommentInput(comment_id=comment_id))
        if existing.note_id != note_id:
            raise CommentNotFoundException(comment_id)
        delete_use_case.execute(DeleteCommentInput(comment_id=comment_id))

    return router
