"""Tag HTTP handlers — thin layer: parse → use-case → response."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from nene2.http import PaginationQueryParser, PaginationResponse
from nene2.validation.exceptions import ValidationError, ValidationException

from .use_case import (
    CreateTagInput,
    CreateTagUseCase,
    DeleteTagInput,
    DeleteTagUseCase,
    GetTagUseCase,
    ListTagsInput,
    ListTagsUseCase,
    UpdateTagInput,
    UpdateTagUseCase,
)


class CreateTagBody(BaseModel):
    name: str


class UpdateTagBody(BaseModel):
    name: str


def make_tag_router(
    list_use_case: ListTagsUseCase,
    get_use_case: GetTagUseCase,
    create_use_case: CreateTagUseCase,
    update_use_case: UpdateTagUseCase,
    delete_use_case: DeleteTagUseCase,
) -> APIRouter:
    router = APIRouter(prefix="/tags", tags=["tags"])
    @router.get("")
    async def list_tags(request: Request) -> JSONResponse:
        pagination = PaginationQueryParser.parse(request)
        output = list_use_case.execute(ListTagsInput(pagination.limit, pagination.offset))
        return JSONResponse(
            PaginationResponse(
                items=[{"id": t.id, "name": t.name} for t in output.items],
                limit=output.limit,
                offset=output.offset,
                total=output.total,
            ).to_dict()
        )

    @router.get("/{tag_id}")
    async def get_tag(tag_id: int) -> JSONResponse:
        tag = get_use_case.execute(tag_id)
        return JSONResponse({"id": tag.id, "name": tag.name})

    @router.post("", status_code=201)
    async def create_tag(body: CreateTagBody) -> JSONResponse:
        errors: list[ValidationError] = []
        if not body.name.strip():
            errors.append(ValidationError("name", "Name must not be empty.", "required"))
        if errors:
            raise ValidationException(errors)

        tag = create_use_case.execute(CreateTagInput(body.name))
        return JSONResponse({"id": tag.id, "name": tag.name}, status_code=201)

    @router.put("/{tag_id}")
    async def update_tag(tag_id: int, body: UpdateTagBody) -> JSONResponse:
        errors: list[ValidationError] = []
        if not body.name.strip():
            errors.append(ValidationError("name", "Name must not be empty.", "required"))
        if errors:
            raise ValidationException(errors)

        tag = update_use_case.execute(UpdateTagInput(tag_id, body.name))
        return JSONResponse({"id": tag.id, "name": tag.name})

    @router.delete("/{tag_id}", status_code=204)
    async def delete_tag(tag_id: int) -> None:
        delete_use_case.execute(DeleteTagInput(tag_id))

    return router
