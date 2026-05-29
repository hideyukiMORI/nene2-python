# Philosophie de conception

## Principes fondamentaux de NENE2

nene2-python partage la même philosophie de conception que PHP NENE2.

### API First

Le contrat de l'API JSON et le schéma OpenAPI sont définis avant le schéma de base de données. Utilisez `uv run python src/scripts/export_openapi.py` pour exporter un `openapi.yaml` statique à tout moment.

### Couche HTTP fine

Les HTTP Handlers ne portent aucune logique métier. La règle est : **parse → use-case → response** — trois étapes, rien de plus. Les règles de domaine vivent dans les UseCases.

### Lisible par les IA

Structure de répertoires explicite, petites classes (≤ 150 lignes), frontières typées — tout cela permet à un LLM de naviguer et modifier le code avec assurance.

### Sécurité d'abord

La sécurité est une contrainte de conception, pas une réflexion après coup :
- Toutes les entrées HTTP validées par Pydantic à la frontière
- Requêtes paramétrées uniquement (prévention des injections SQL)
- `secrets.compare_digest` pour une comparaison de tokens protégée contre les attaques temporelles
- En-têtes de sécurité appliqués par le middleware à chaque réponse

### Prêt pour la livraison LLM

Comme les UseCases sont indépendants de HTTP et de la base de données, ils peuvent être enregistrés directement comme outils MCP. `src/example/mcp.py` le démontre — 15 outils, sans plomberie supplémentaire. Voir [Un UseCase, deux surfaces (HTTP + MCP)](one-usecase-two-surfaces.md) pour le code côte à côte et le test de parité qui le protège.

---

## Python vs PHP NENE2

| PHP | Python | Notes |
|---|---|---|
| `readonly class` | `@dataclass(frozen=True, slots=True)` | Objet valeur immuable |
| `ValidationException` + `ValidationError` | Mêmes noms (`nene2.validation`) | 422 + Problem Details |
| `PaginationQueryParser` | `nene2.http.PaginationQueryParser` | Parsing des paramètres de requête |
| `PaginationResponse` | `nene2.http.PaginationResponse` | Réponse paginée |
| `ProblemDetailsResponseFactory` | `nene2.http.problem_details_response()` | RFC 9457 |
| `ErrorHandlerMiddleware` | `nene2.middleware.ErrorHandlerMiddleware` | Capture toutes les exceptions |
| `PHPStan level 8` | `mypy --strict` | Sécurité de type maximale |
| `PHP-CS-Fixer` | `ruff format` | Formatage du code |
| `UseCaseInterface` | `nene2.use_case.UseCaseProtocol[I, O]` | Typage structurel |

## Fonctionnalités exclusives à Python

| Fonctionnalité | Avantage Python |
|---|---|
| `AsyncUseCaseProtocol[I, O]` | Pas d'équivalent PHP — protocole coroutine natif |
| Génération OpenAPI automatique | FastAPI génère Swagger UI / ReDoc sans configuration |
| async/await natif | FastAPI + uvicorn — I/O non bloquant de bout en bout |
| MCP SDK | Le SDK Python d'Anthropic est l'implémentation de référence |
| `mypy --strict` | Plus strict que PHPStan level 8 en pratique |

## Index des ADR

Les décisions de conception individuelles sont enregistrées dans des Architecture Decision Records :

- [ADR-0001 : Toolchain](../adr/0001-toolchain.md)
- [ADR-0002 : Clean Architecture](../adr/0002-clean-architecture.md)
- [ADR-0003 : Security First](../adr/0003-security-first.md)
- [ADR-0004 : AI-First Design](../adr/0004-ai-first-design.md)
- [ADR-0005 : Logging](../adr/0005-logging.md)
- [ADR-0006 : Rate Limiting](../adr/0006-rate-limiting.md)
- [ADR-0009 : MCP Design](../adr/0009-mcp-design.md)
- [ADR-0010 : AsyncUseCase Pattern](../adr/0010-async-use-case.md)
