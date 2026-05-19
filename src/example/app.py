"""Application factory — wires dependencies and registers routes."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from nene2.auth import ApiKeyAuthMiddleware, BearerTokenMiddleware, LocalTokenVerifier
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
    ThrottleMiddleware,
)
from nene2.middleware.error_handler import request_validation_error_handler
from nene2.validation.exceptions import ValidationException

from .comment.exceptions import CommentNotFoundExceptionHandler
from .comment.handler import make_comment_router
from .comment.repository import CommentRepositoryInterface, InMemoryCommentRepository
from .comment.sqlalchemy_repository import SqlAlchemyCommentRepository
from .comment.use_case import (
    CreateCommentUseCase,
    DeleteCommentUseCase,
    GetCommentUseCase,
    ListCommentsUseCase,
    UpdateCommentUseCase,
)
from .note.exceptions import NoteNotFoundExceptionHandler
from .note.handler import make_note_router
from .note.repository import InMemoryNoteRepository, NoteRepositoryInterface
from .note.sqlalchemy_repository import SqlAlchemyNoteRepository
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
from .tag.sqlalchemy_repository import SqlAlchemyTagRepository
from .tag.use_case import (
    CreateTagUseCase,
    DeleteTagUseCase,
    GetTagUseCase,
    ListTagsUseCase,
    UpdateTagUseCase,
)

type _Repos = tuple[
    NoteRepositoryInterface,
    TagRepositoryInterface,
    CommentRepositoryInterface,
    DatabaseQueryExecutorInterface | None,
]


def _build_repositories(cfg: AppSettings) -> _Repos:
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
        return (
            SqlAlchemyNoteRepository(executor),
            SqlAlchemyTagRepository(executor),
            SqlAlchemyCommentRepository(executor),
            executor,
        )
    if cfg.db_adapter in ("mysql", "pgsql"):
        engine = create_engine(cfg.db_url)
        executor = SqlAlchemyQueryExecutor(engine)
        return (
            SqlAlchemyNoteRepository(executor),
            SqlAlchemyTagRepository(executor),
            SqlAlchemyCommentRepository(executor),
            executor,
        )
    return InMemoryNoteRepository(), InMemoryTagRepository(), InMemoryCommentRepository(), None


def create_app(settings: AppSettings | None = None) -> FastAPI:
    cfg = settings or AppSettings()
    setup_logging(cfg.app_env)

    app = FastAPI(
        title=cfg.app_name,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Registration order: innermost first, outermost last.
    # Starlette executes in reverse — the last registered wraps all others.
    app.add_middleware(
        ErrorHandlerMiddleware,
        debug=cfg.app_debug,
        domain_handlers=[
            NoteNotFoundExceptionHandler(),
            TagNotFoundExceptionHandler(),
            CommentNotFoundExceptionHandler(),
        ],
    )
    if cfg.security_headers_enabled:
        app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=cfg.max_body_size)
    if cfg.throttle_enabled:
        app.add_middleware(
            ThrottleMiddleware,
            limit=cfg.throttle_limit,
            window=cfg.throttle_window,
        )
    # Auth sits inside the CORS layer so preflight OPTIONS bypasses auth checks.
    if cfg.bearer_token_enabled:
        app.add_middleware(
            BearerTokenMiddleware,
            verifier=LocalTokenVerifier(cfg.bearer_tokens),
        )
    if cfg.api_key_enabled:
        app.add_middleware(
            ApiKeyAuthMiddleware,
            verifier=LocalTokenVerifier(cfg.api_keys),
        )
    # CORS must be outermost — register last so preflight OPTIONS is handled
    # before throttle, auth, or any other middleware runs.
    if cfg.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cfg.cors_origins,
            allow_credentials=cfg.cors_allow_credentials,
            allow_methods=cfg.cors_allow_methods,
            allow_headers=cfg.cors_allow_headers,
        )
    app.add_exception_handler(
        ValidationException,
        ErrorHandlerMiddleware.handle_validation_exception,
    )
    app.add_exception_handler(
        RequestValidationError,
        request_validation_error_handler,
    )

    note_repo, tag_repo, comment_repo, db_executor = _build_repositories(cfg)

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

    app.include_router(
        make_comment_router(
            ListCommentsUseCase(comment_repo, note_repo),
            GetCommentUseCase(comment_repo),
            CreateCommentUseCase(comment_repo, note_repo),
            UpdateCommentUseCase(comment_repo),
            DeleteCommentUseCase(comment_repo),
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
