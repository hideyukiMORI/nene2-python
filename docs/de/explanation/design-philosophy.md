# Designphilosophie

## NENE2-Grundprinzipien

nene2-python teilt dieselbe Designphilosophie wie PHP NENE2.

### API First

Der JSON-API-Vertrag und das OpenAPI-Schema werden vor dem Datenbankschema definiert. Verwenden Sie `uv run python src/scripts/export_openapi.py`, um jederzeit eine statische `openapi.yaml` zu exportieren.

### Dünne HTTP-Schicht

HTTP-Handler besitzen keine Geschäftslogik. Die Regel lautet: **parse → use-case → response** — drei Schritte, nicht mehr. Domänenregeln leben in UseCases.

### AI-lesbar

Explizite Verzeichnisstruktur, kleine Klassen (≤ 150 Zeilen), typisierte Grenzen — diese Merkmale ermöglichen es einem LLM, die Codebasis sicher zu navigieren und zu bearbeiten.

### Security First

Sicherheit ist eine Designanforderung, kein nachträglicher Gedanke:
- Alle HTTP-Eingaben werden an der Grenze durch Pydantic validiert
- Ausschließlich parametrisierte Abfragen (SQL-Injection-Schutz)
- `secrets.compare_digest` für zeitkonstanten Token-Vergleich
- Sicherheitsheader werden durch Middleware bei jeder Antwort angewendet

### LLM Delivery Ready

Da UseCases unabhängig von HTTP und Datenbank sind, können sie direkt als MCP-Tools registriert werden. `src/example/mcp.py` belegt dies — 15 Tools, keinerlei zusätzliche Verdrahtung. Siehe [Ein UseCase, zwei Oberflächen (HTTP + MCP)](one-usecase-two-surfaces.md) für den Side-by-Side-Code und den Paritätstest, der dies absichert.

---

## Python vs. PHP NENE2

| PHP | Python | Hinweise |
|---|---|---|
| `readonly class` | `@dataclass(frozen=True, slots=True)` | Unveränderliches Wertobjekt |
| `ValidationException` + `ValidationError` | Gleiche Namen (`nene2.validation`) | 422 + Problem Details |
| `PaginationQueryParser` | `nene2.http.PaginationQueryParser` | Query-Parameter-Parsing |
| `PaginationResponse` | `nene2.http.PaginationResponse` | Paginierte Antwort |
| `ProblemDetailsResponseFactory` | `nene2.http.problem_details_response()` | RFC 9457 |
| `ErrorHandlerMiddleware` | `nene2.middleware.ErrorHandlerMiddleware` | Fängt alle Ausnahmen ab |
| `PHPStan level 8` | `mypy --strict` | Maximale Typsicherheit |
| `PHP-CS-Fixer` | `ruff format` | Code-Formatierung |
| `UseCaseInterface` | `nene2.use_case.UseCaseProtocol[I, O]` | Strukturelles Typing |

## Nur in Python verfügbare Features

| Feature | Warum Python hier überlegen ist |
|---|---|
| `AsyncUseCaseProtocol[I, O]` | Kein PHP-Äquivalent — natives Coroutine-Protokoll |
| Automatische OpenAPI-Generierung | FastAPI generiert Swagger UI / ReDoc ohne Konfiguration |
| Natives async/await | FastAPI + uvicorn — durchgehend nicht-blockierende I/O |
| MCP SDK | Anthropics Python-SDK ist die Referenzimplementierung |
| `mypy --strict` | In der Praxis strenger als PHPStan Level 8 |

## ADR-Index

Einzelne Designentscheidungen sind in Architecture Decision Records festgehalten:

- [ADR-0001: Toolchain](../adr/0001-toolchain.md)
- [ADR-0002: Clean Architecture](../adr/0002-clean-architecture.md)
- [ADR-0003: Security First](../adr/0003-security-first.md)
- [ADR-0004: AI-First Design](../adr/0004-ai-first-design.md)
- [ADR-0005: Logging](../adr/0005-logging.md)
- [ADR-0006: Rate Limiting](../adr/0006-rate-limiting.md)
- [ADR-0009: MCP Design](../adr/0009-mcp-design.md)
- [ADR-0010: AsyncUseCase Pattern](../adr/0010-async-use-case.md)
