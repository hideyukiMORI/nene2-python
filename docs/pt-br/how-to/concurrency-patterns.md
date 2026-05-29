# Como fazer: escolher um padrão de concorrência

Um guia consolidando os achados do FT188 (threading) ao FT192 (asyncio).
No nene2-python a **camada UseCase é independente de HTTP**, então a escolha de
concorrência é feita no UseCase ou na camada do HTTP handler.

---

## Tabela de seleção rápida

| Caso de uso | Recomendado | FT |
|---|---|---|
| Aguardando I/O dentro de um handler FastAPI | `async def` + `await` | FT192 |
| Executar um UseCase síncrono sem bloquear | `AsyncUseCaseProtocol` | FT6, FT14 |
| Descarregar trabalho CPU-bound em uma thread | `asyncio.to_thread()` ou `ThreadPoolExecutor` | FT188, FT191 |
| Descarregar trabalho CPU-bound em um processo | `ProcessPoolExecutor` / `multiprocessing` | FT190, FT191 |
| Comando externo em background | `subprocess` (`shell=False` + allowlist) | FT189 |
| Cache compartilhado em memória | `TtlCache[V]` (thread-safe) | FT119, FT171 |

---

## asyncio (FT192)

As rotas FastAPI são `async def` por padrão. Para paralelizar múltiplas operações de I/O:

```python
import asyncio

async def execute(self, input_: ListNotesInput) -> ListNotesOutput:
    items_task = asyncio.create_task(self._repository.find_all_async(...))
    total_task = asyncio.create_task(self._repository.count_async())
    items, total = await asyncio.gather(items_task, total_task)
    return ListNotesOutput(items=items, total=total, ...)
```

**Atenção**: O Pydantic v2 trunca `float` para `int`. Torne os limites numéricos explícitos com
`Field(ge=..., le=...)`.

---

## threading (FT188)

Sob o GIL, não serve para paralelismo de CPU, mas é útil como ponte para
**APIs legadas cujo I/O bloqueante não foi tornado assíncrono**.

- `threading.Lock` / `asyncio.Lock` — protegem estado compartilhado
- `ThreadPoolExecutor` — descarrega funções síncronas (combine com FT191)

---

## subprocess (FT189)

**Regras obrigatórias** (CLAUDE.md / diagnóstico de segurança FT189):

1. Apenas `shell=False`
2. Valide o nome do comando contra uma allowlist
3. Defina um timeout e um limite de tamanho do stdout
4. `# noqa: S603` para o ruff apenas após a verificação da allowlist (declare o motivo na docstring)

---

## Alinhamento com o nene2

| Camada | Concorrência |
|---|---|
| UseCase | `AsyncUseCaseProtocol` ou puro-síncrono (testável com InMemory) |
| HTTP | handlers `async def`, `BackgroundTasks` ([background-tasks.md](background-tasks.md)) |
| Middleware | ASGI síncrono; não coloque trabalho bloqueante dentro do middleware |
| MCP | exponha o UseCase como ferramenta diretamente — a concorrência fica dentro do UseCase |

Relatórios detalhados: [FT188](../field-trials/2026-05-field-trial-188.md) · [FT189](../field-trials/2026-05-field-trial-189.md) · [FT190](../field-trials/2026-05-field-trial-190.md) · [FT191](../field-trials/2026-05-field-trial-191.md) · [FT192](../field-trials/2026-05-field-trial-192.md)
