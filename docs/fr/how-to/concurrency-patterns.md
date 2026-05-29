# Guide pratique : choisir un schéma de concurrence

Un guide qui consolide les résultats de FT188 (threading) à FT192 (asyncio).
Dans nene2-python, la **couche UseCase est indépendante de HTTP**, donc le choix de la
concurrence se fait dans le UseCase ou la couche handler HTTP.

---

## Tableau de sélection rapide

| Cas d'usage | Recommandé | FT |
|---|---|---|
| Attendre des I/O dans un handler FastAPI | `async def` + `await` | FT192 |
| Exécuter un UseCase sync sans blocage | `AsyncUseCaseProtocol` | FT6, FT14 |
| Déléguer du travail CPU à un thread | `asyncio.to_thread()` ou `ThreadPoolExecutor` | FT188, FT191 |
| Déléguer du travail CPU à un processus | `ProcessPoolExecutor` / `multiprocessing` | FT190, FT191 |
| Commande externe en arrière-plan | `subprocess` (`shell=False` + allowlist) | FT189 |
| Cache partagé en mémoire | `TtlCache[V]` (thread-safe) | FT119, FT171 |

---

## asyncio (FT192)

Les routes FastAPI sont `async def` par défaut. Pour paralléliser plusieurs opérations I/O :

```python
import asyncio

async def execute(self, input_: ListNotesInput) -> ListNotesOutput:
    items_task = asyncio.create_task(self._repository.find_all_async(...))
    total_task = asyncio.create_task(self._repository.count_async())
    items, total = await asyncio.gather(items_task, total_task)
    return ListNotesOutput(items=items, total=total, ...)
```

**Note** : Pydantic v2 tronque les `float` en `int`. Rendez les bornes numériques explicites avec
`Field(ge=..., le=...)`.

---

## threading (FT188)

Sous le GIL, cela ne convient pas au parallélisme CPU, mais c'est utile comme passerelle vers
**les API legacy dont les I/O bloquantes n'ont pas encore été rendues async**.

- `threading.Lock` / `asyncio.Lock` — protéger les états partagés
- `ThreadPoolExecutor` — déléguer des fonctions sync (combiner avec FT191)

---

## subprocess (FT189)

**Règles obligatoires** (CLAUDE.md / diagnostic de sécurité FT189) :

1. `shell=False` uniquement
2. Valider le nom de la commande contre une allowlist
3. Définir un timeout et une limite de taille stdout
4. `# noqa: S603` pour ruff uniquement après la vérification de l'allowlist (indiquer la raison dans la docstring)

---

## Alignement avec nene2

| Couche | Concurrence |
|---|---|
| UseCase | `AsyncUseCaseProtocol` ou pur-sync (testable avec InMemory) |
| HTTP | handlers `async def`, `BackgroundTasks` ([background-tasks.md](background-tasks.md)) |
| Middleware | ASGI synchrone ; ne pas mettre de travail bloquant dans le middleware |
| MCP | exposer le UseCase directement comme outil — la concurrence reste dans le UseCase |

Rapports détaillés : [FT188](../field-trials/2026-05-field-trial-188.md) · [FT189](../field-trials/2026-05-field-trial-189.md) · [FT190](../field-trials/2026-05-field-trial-190.md) · [FT191](../field-trials/2026-05-field-trial-191.md) · [FT192](../field-trials/2026-05-field-trial-192.md)
