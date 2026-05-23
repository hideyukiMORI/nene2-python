# AGENTS.md — nene2-python

AI エージェントがこのリポジトリで作業を始めるためのエントリーポイント。

## このリポジトリについて

NENE2 の設計哲学を Python で実装したリファレンスフレームワーク。

- HTTP 層: FastAPI + Starlette（ASGI）
- DTO / バリデーション: Pydantic v2 + `dataclass(frozen=True)`
- 型チェック: `mypy --strict`
- Lint / Format: `ruff`
- テスト: `pytest` + `httpx`（466 tests、カバレッジ 80% 以上）
- 現状: **v1.8.97** / FT219 完了 / [Field Trial INDEX](docs/field-trials/INDEX.md)

## 設計原則（PHP 版 NENE2 と共通）

1. UseCase / Domain は HTTP・DB から完全独立
2. 境界は interface（ABC）で定義
3. ハンドラーは薄く: parse → use-case → response
4. エラーは RFC 9457 Problem Details（application/problem+json）
5. `ValidationException` → 422 自動マッピング
6. FastAPI アプリは `APIRouter` + `create_app()` をファイル末尾に配置（[CLAUDE.md](CLAUDE.md)）

## 全チェックコマンド（CI と同等）

```bash
uv run pytest && \
uv run mypy src/ && \
uv run ruff check src/ tests/ && \
uv run ruff format --check src/ tests/ && \
uv run pip-audit --ignore-vuln PYSEC-2025-183
```

## ドキュメント入口

| 用途 | ファイル |
|---|---|
| 設計ポリシー（SSOT） | [CLAUDE.md](CLAUDE.md) |
| 現状・次タスク | [docs/todo/current.md](docs/todo/current.md) |
| FT 一覧 | [docs/field-trials/INDEX.md](docs/field-trials/INDEX.md) |
| API リファレンス | [docs/reference/framework-modules.md](docs/reference/framework-modules.md) |
| How-to | [docs/how-to/](docs/how-to/) |

## PHP 版リポジトリとの関係

PHP 版 NENE2 の設計決定・ADR・フィールドトライアル記録は `../NENE2/docs/` を参照。
この Python 版は同じ原則に従い、Python のイディオムで実装する。

## 作業ガイドライン

- 詳細は `CLAUDE.md` を参照
- 変更は GitHub Issue ベースで進める
- `main` へ直接コミットしない
- PR 前に全チェックを通過させる
