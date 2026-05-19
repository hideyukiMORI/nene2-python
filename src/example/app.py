"""Application factory — wires dependencies and registers routes."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from nene2.config import AppSettings
from nene2.middleware import ErrorHandlerMiddleware
from nene2.validation.exceptions import ValidationException

from .note.exceptions import NoteNotFoundExceptionHandler
from .note.handler import make_note_router
from .note.repository import InMemoryNoteRepository
from .note.use_case import (
    CreateNoteUseCase,
    DeleteNoteUseCase,
    GetNoteUseCase,
    ListNotesUseCase,
    UpdateNoteUseCase,
)
from .tag.exceptions import TagNotFoundExceptionHandler
from .tag.handler import make_tag_router
from .tag.repository import InMemoryTagRepository
from .tag.use_case import (
    CreateTagUseCase,
    DeleteTagUseCase,
    GetTagUseCase,
    ListTagsUseCase,
    UpdateTagUseCase,
)


def create_app(settings: AppSettings | None = None) -> FastAPI:
    cfg = settings or AppSettings()

    app = FastAPI(
        title=cfg.app_name,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        ErrorHandlerMiddleware,
        debug=cfg.app_debug,
        domain_handlers=[NoteNotFoundExceptionHandler(), TagNotFoundExceptionHandler()],
    )
    app.add_exception_handler(
        ValidationException,
        ErrorHandlerMiddleware.handle_validation_exception,
    )

    # Wire note domain
    note_repo = InMemoryNoteRepository()
    app.include_router(
        make_note_router(
            ListNotesUseCase(note_repo),
            GetNoteUseCase(note_repo),
            CreateNoteUseCase(note_repo),
            UpdateNoteUseCase(note_repo),
            DeleteNoteUseCase(note_repo),
        )
    )

    # Wire tag domain
    tag_repo = InMemoryTagRepository()
    app.include_router(
        make_tag_router(
            ListTagsUseCase(tag_repo),
            GetTagUseCase(tag_repo),
            CreateTagUseCase(tag_repo),
            UpdateTagUseCase(tag_repo),
            DeleteTagUseCase(tag_repo),
        )
    )

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return app


app = create_app()
