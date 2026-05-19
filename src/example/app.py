"""Application factory — wires dependencies and registers routes."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from nene2.config import AppSettings
from nene2.middleware import ErrorHandlerMiddleware
from nene2.validation.exceptions import ValidationException

from .note.handler import make_note_router
from .note.repository import InMemoryNoteRepository
from .note.use_case import CreateNoteUseCase, GetNoteUseCase, ListNotesUseCase


def create_app(settings: AppSettings | None = None) -> FastAPI:
    cfg = settings or AppSettings()

    app = FastAPI(
        title=cfg.app_name,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(ErrorHandlerMiddleware, debug=cfg.app_debug)
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
        )
    )

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return app


app = create_app()
