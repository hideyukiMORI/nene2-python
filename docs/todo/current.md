# TODO — current (v0.2.0 作業)

最終更新: 2026-05-19
対象マイルストーン: v0.2.0 — Write Operations & Domain Exceptions

---

## 優先順位ルール

1. **ブロッカー**: CI がなければ他の作業が不安定 → GitHub Actions を最初に立てる
2. **Note フル CRUD**: 既存コードの拡張なので最小コスト
3. **ドメイン例外パターン**: Note と Tag で共通パターンを確立してから Tag に横展開
4. **Tag**: Note の構造をコピーして展開

---

## v0.2.0 タスク一覧

### 🔴 最優先（ブロッカー）

- [ ] **GitHub Actions CI** (`feat/issue-1-github-actions-ci`)
  - `.github/workflows/ci.yml`
  - jobs: pytest, mypy, ruff check, ruff format --check, pip-audit
  - Python matrix: 3.12
  - uv でキャッシュ

- [ ] **`.env.example`** (`feat/issue-2-env-example`)
  - 全環境変数のキー一覧（値は空またはデフォルト値）
  - `.gitignore` に `.env` を追加

---

### 🟠 Note フル CRUD

- [ ] **`NoteNotFoundException`** + `DomainExceptionHandlerProtocol`
  - `src/nene2/error/domain_exception_handler.py` に Protocol 定義
  - `src/example/note/exceptions.py` に `NoteNotFoundException`
  - `ErrorHandlerMiddleware` が `DomainExceptionHandlerProtocol` のリストを受け取る設計に拡張

- [ ] **`UpdateNoteUseCase`** + **`UpdateNoteHandler`**
  - `UpdateNoteInput(note_id: int, title: str, body: str)`
  - `NoteRepositoryInterface.update()` メソッドを追加
  - `InMemoryNoteRepository.update()` 実装
  - Handler: `PUT /notes/{note_id}` → 200 / 404

- [ ] **`DeleteNoteUseCase`** + **`DeleteNoteHandler`**
  - `DeleteNoteInput(note_id: int)`
  - `NoteRepositoryInterface.delete()` メソッドを追加
  - `InMemoryNoteRepository.delete()` 実装
  - Handler: `DELETE /notes/{note_id}` → 204 / 404

---

### 🟡 Tag フル CRUD

Note の実装完了後に着手すること。構造は Note の完全な同型コピーから始める。

- [ ] **`Tag` Entity** + `TagRepositoryInterface` + `InMemoryTagRepository`
  - `src/example/tag/entity.py`, `repository.py`

- [ ] **`TagNotFoundException`**

- [ ] **Tag UseCases** (5本)
  - `ListTagsUseCase`, `GetTagUseCase`, `CreateTagUseCase`, `UpdateTagUseCase`, `DeleteTagUseCase`

- [ ] **Tag Handlers** (5本)
  - `GET /tags`, `GET /tags/{tag_id}`, `POST /tags`, `PUT /tags/{tag_id}`, `DELETE /tags/{tag_id}`

- [ ] **Tag をアプリに配線** (`src/example/app.py`)

---

### 🟢 Health Check

- [ ] **`HealthCheckProtocol`** in `src/nene2/http/health.py`
  - `check() -> HealthStatus` (dataclass: `status: str`, `checks: dict[str, str]`)

- [ ] **`GET /health`** エンドポイント
  - 200 `{"status": "ok"}` / 503 `{"status": "degraded", "checks": {...}}`

---

## 作業ルール

- 各タスクは GitHub Issue を立ててから着手
- ブランチ名: `feat/issue-{N}-{kebab-summary}`
- PR 前に全チェック通過: `uv run pytest && uv run mypy src/ && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run pip-audit`
- テスト: 新しい UseCase・Handler には必ず pytest を書く
- 1 PR = 1 タスク（混ぜない）

---

## 完了定義（v0.2.0）

以下が全て満たされること:

```bash
# CI が green
uv run pytest && uv run mypy src/ && uv run ruff check src/ tests/ && uv run pip-audit

# 全エンドポイントが動作
curl -X GET    http://localhost:8080/notes
curl -X POST   http://localhost:8080/notes   -d '{"title":"T","body":"B"}'
curl -X PUT    http://localhost:8080/notes/1 -d '{"title":"T2","body":"B2"}'
curl -X DELETE http://localhost:8080/notes/1
curl -X GET    http://localhost:8080/tags
curl -X POST   http://localhost:8080/tags    -d '{"name":"python"}'
curl -X PUT    http://localhost:8080/tags/1  -d '{"name":"py"}'
curl -X DELETE http://localhost:8080/tags/1
curl -X GET    http://localhost:8080/health
```
