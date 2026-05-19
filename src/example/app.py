"""Application factory — wires dependencies and registers routes."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from nene2.config import AppSettings
from nene2.database import (
    DatabaseHealthCheck,
    DatabaseQueryExecutorInterface,
    SqlAlchemyQueryExecutor,
)
from nene2.http import HealthStatus
from nene2.log import setup_logging
from nene2.middleware import (
    ErrorHandlerMiddleware,
    RequestIdMiddleware,
    RequestLoggingMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from nene2.validation.exceptions import ValidationException

from .note.exceptions import NoteNotFoundExceptionHandler
from .note.handler import make_note_router
from .note.repository import InMemoryNoteRepository, NoteRepositoryInterface
from .note.sqlite_repository import SqliteNoteRepository
from .note.use_case import (
    CreateNoteUseCase,
    DeleteNoteUseCase,
    GetNoteUseCase,
    ListNotesUseCase,
    UpdateNoteUseCase,
)
from .schema import ensure_schema
from .tag.exceptions import TagNotFoundExceptionHandler
from .tag.handler import make_tag_router
from .tag.repository import InMemoryTagRepository, TagRepositoryInterface
from .tag.sqlite_repository import SqliteTagRepository
from .tag.use_case import (
    CreateTagUseCase,
    DeleteTagUseCase,
    GetTagUseCase,
    ListTagsUseCase,
    UpdateTagUseCase,
)


def _build_repositories(
    cfg: AppSettings,
) -> tuple[NoteRepositoryInterface, TagRepositoryInterface, DatabaseQueryExecutorInterface | None]:
    """Build repositories based on DB_ADAPTER setting."""
    if cfg.db_adapter == "sqlite":
        is_memory = cfg.db_name == ":memory:"
        engine = create_engine(
            cfg.db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool if is_memory else None,
        )
        ensure_schema(engine)
        executor = SqlAlchemyQueryExecutor(engine)
        return SqliteNoteRepository(executor), SqliteTagRepository(executor), executor
    return InMemoryNoteRepository(), InMemoryTagRepository(), None


def create_app(settings: AppSettings | None = None) -> FastAPI:
    cfg = settings or AppSettings()
    setup_logging(cfg.app_env)

    app = FastAPI(
        title=cfg.app_name,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=cfg.max_body_size)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    if cfg.security_headers_enabled:
        app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        ErrorHandlerMiddleware,
        debug=cfg.app_debug,
        domain_handlers=[NoteNotFoundExceptionHandler(), TagNotFoundExceptionHandler()],
    )
    app.add_exception_handler(
        ValidationException,
        ErrorHandlerMiddleware.handle_validation_exception,
    )

    note_repo, tag_repo, db_executor = _build_repositories(cfg)

    app.include_router(
        make_note_router(
            ListNotesUseCase(note_repo),
            GetNoteUseCase(note_repo),
            CreateNoteUseCase(note_repo),
            UpdateNoteUseCase(note_repo),
            DeleteNoteUseCase(note_repo),
        )
    )

    app.include_router(
        make_tag_router(
            ListTagsUseCase(tag_repo),
            GetTagUseCase(tag_repo),
            CreateTagUseCase(tag_repo),
            UpdateTagUseCase(tag_repo),
            DeleteTagUseCase(tag_repo),
        )
    )

    db_health = DatabaseHealthCheck(db_executor) if db_executor else None

    @app.get("/health", tags=["system"], summary="Health check")
    async def health() -> JSONResponse:
        status = db_health.check() if db_health else HealthStatus(status="ok")
        code = 200 if status.is_healthy else 503
        return JSONResponse({"status": status.status, "checks": status.checks}, status_code=code)

    return app


app = create_app()
