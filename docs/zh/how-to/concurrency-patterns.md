# 操作指南：选择并发模式

本指南整合了 FT188（threading）到 FT192（asyncio）的发现。在 nene2-python 中，**UseCase 层与 HTTP 无关**，因此并发模式的选择在 UseCase 或 HTTP handler 层做出。

---

## 快速选型表

| 使用场景 | 推荐方案 | FT |
|---|---|---|
| 在 FastAPI handler 中等待 I/O | `async def` + `await` | FT192 |
| 以非阻塞方式运行同步 UseCase | `AsyncUseCaseProtocol` | FT6, FT14 |
| 将 CPU 密集型工作卸载到线程 | `asyncio.to_thread()` 或 `ThreadPoolExecutor` | FT188, FT191 |
| 将 CPU 密集型工作卸载到进程 | `ProcessPoolExecutor` / `multiprocessing` | FT190, FT191 |
| 在后台执行外部命令 | `subprocess`（`shell=False` + 允许列表） | FT189 |
| 共享内存缓存 | `TtlCache[V]`（线程安全） | FT119, FT171 |

---

## asyncio（FT192）

FastAPI 路由默认为 `async def`。若要并行化多个 I/O 操作：

```python
import asyncio

async def execute(self, input_: ListNotesInput) -> ListNotesOutput:
    items_task = asyncio.create_task(self._repository.find_all_async(...))
    total_task = asyncio.create_task(self._repository.count_async())
    items, total = await asyncio.gather(items_task, total_task)
    return ListNotesOutput(items=items, total=total, ...)
```

**注意**：Pydantic v2 会将 `float` 截断为 `int`。请使用 `Field(ge=..., le=...)` 显式指定数值边界。

---

## threading（FT188）

在 GIL 限制下，threading 不适合 CPU 并行，但可用于**桥接尚未异步化的遗留阻塞 I/O API**。

- `threading.Lock` / `asyncio.Lock` — 保护共享状态
- `ThreadPoolExecutor` — 卸载同步函数（与 FT191 结合使用）

---

## subprocess（FT189）

**强制规则**（CLAUDE.md / FT189 安全诊断）：

1. 仅使用 `shell=False`
2. 将命令名称与允许列表进行校验
3. 设置超时和 stdout 大小限制
4. 仅在允许列表校验后对 ruff 使用 `# noqa: S603`（在文档字符串中说明原因）

---

## 与 nene2 的对齐方式

| 层 | 并发方式 |
|---|---|
| UseCase | `AsyncUseCaseProtocol` 或纯同步（InMemory 可测试） |
| HTTP | `async def` handler、`BackgroundTasks`（[background-tasks.md](background-tasks.md)） |
| Middleware | 同步 ASGI；不要在 middleware 中放置阻塞操作 |
| MCP | 直接将 UseCase 作为工具暴露 — 并发保留在 UseCase 内部 |

详细报告：[FT188](../field-trials/2026-05-field-trial-188.md) · [FT189](../field-trials/2026-05-field-trial-189.md) · [FT190](../field-trials/2026-05-field-trial-190.md) · [FT191](../field-trials/2026-05-field-trial-191.md) · [FT192](../field-trials/2026-05-field-trial-192.md)
