# ADR-0005 — Logging: structlog with JSON output

Date: 2026-05-19  
Status: Accepted

## Context

We need structured, machine-readable logs for production observability. Python's stdlib `logging` is text-oriented and composing contextual fields (request_id, user_id) requires thread-locals or manual key passing. PHP NENE2 uses Monolog with JSON formatter.

## Decision

- **structlog ≥ 24.0** as the logging library
- `setup_logging(app_env)` configures stdlib root logger to route through structlog
- `app_env == "local"` → ConsoleRenderer (colored, human-readable)
- `app_env != "local"` → JSONRenderer (one JSON object per line, machine-readable)
- Contextual fields (request_id, method, path, status_code, duration_ms) bound via `structlog.contextvars` — no arguments passed between functions
- `RequestLoggingMiddleware` clears and rebinds context per request
- `print()` is forbidden (ruff T20 rule); use `structlog.get_logger(__name__).info(...)` instead

## Consequences

- Log lines in production are valid JSON — parseable by Datadog, Loki, CloudWatch without config
- Request ID automatically appears in all log lines emitted during a request (via contextvars)
- `setup_logging()` must be called once at app startup; tests do not call it (stdlib logging captures output)
