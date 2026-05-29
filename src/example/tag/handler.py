"""Tag HTTP handlers — thin layer: parse → use-case → response."""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from nene2.http import PaginationQueryParser

from .use_case import (
    MAX_TAG_NAME_LENGTH,
    CreateTagInput,
    CreateTagUseCase,
    DeleteTagInput,
    DeleteTagUseCase,
    GetTagInput,
    GetTagUseCase,
    ListTagsInput,
    ListTagsUseCase,
    UpdateTagInput,
    UpdateTagUseCase,
)


class CreateTagBody(BaseModel):
    name: str = Field(max_length=MAX_TAG_NAME_LENGTH, description="Tag name.")


class UpdateTagBody(BaseModel):
    name: str = Field(max_length=MAX_TAG_NAME_LENGTH, description="Tag name.")


class TagResponse(BaseModel):
    id: int = Field(description="Tag identifier.")
    name: str = Field(description="Tag name.")


class TagListResponse(BaseModel):
    items: list[TagResponse] = Field(description="Tags on this page.")
    limit: int = Field(description="Page size.")
    offset: int = Field(description="Page offset.")
    total: int = Field(description="Total number of tags.")


def make_tag_router(
    list_use_case: ListTagsUseCase,
    get_use_case: GetTagUseCase,
    create_use_case: CreateTagUseCase,
    update_use_case: UpdateTagUseCase,
    delete_use_case: DeleteTagUseCase,
) -> APIRouter:
    router = APIRouter(prefix="/tags", tags=["tags"])

    @router.get("", response_model=TagListResponse, summary="List tags")
    async def list_tags(request: Request) -> TagListResponse:
        pagination = PaginationQueryParser.parse(request)
        output = list_use_case.execute(ListTagsInput(pagination.limit, pagination.offset))
        return TagListResponse(
            items=[TagResponse(id=t.id, name=t.name) for t in output.items],
            limit=output.limit,
            offset=output.offset,
            total=output.total,
        )

    @router.get("/{tag_id}", response_model=TagResponse, summary="Get a tag")
    async def get_tag(tag_id: int) -> TagResponse:
        tag = get_use_case.execute(GetTagInput(tag_id))
        return TagResponse(id=tag.id, name=tag.name)

    @router.post("", status_code=201, response_model=TagResponse, summary="Create a tag")
    async def create_tag(body: CreateTagBody) -> TagResponse:
        tag = create_use_case.execute(CreateTagInput(body.name))
        return TagResponse(id=tag.id, name=tag.name)

    @router.put("/{tag_id}", response_model=TagResponse, summary="Update a tag")
    async def update_tag(tag_id: int, body: UpdateTagBody) -> TagResponse:
        tag = update_use_case.execute(UpdateTagInput(tag_id, body.name))
        return TagResponse(id=tag.id, name=tag.name)

    @router.delete("/{tag_id}", status_code=204, summary="Delete a tag")
    async def delete_tag(tag_id: int) -> None:
        delete_use_case.execute(DeleteTagInput(tag_id))

    return router
