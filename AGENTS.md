# AGENTS.md — nene2-python

AI エージェントがこのリポジトリで作業を始めるためのエントリーポイント。

## このリポジトリについて

NENE2 の設計哲学を Python で実装したリファレンスフレームワーク。

- HTTP 層: FastAPI + Starlette（ASGI）
- DTO / バリデーション: Pydantic v2 + `dataclass(frozen=True)`
- 型チェック: `mypy --strict`
- Lint / Format: `ruff`
- テスト: `pytest` + `httpx`

## 設計原則（PHP 版 NENE2 と共通）

1. UseCase / Domain は HTTP・DB から完全独立
2. 境界は interface（ABC）で定義
3. ハンドラーは薄く: parse → use-case → response
4. エラーは RFC 9457 Problem Details（application/problem+json）
5. `ValidationException` → 422 自動マッピング

## 全チェックコマンド（CI と同等）

```bash
uv run pytest && uv run mypy src/ && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/
```

## PHP 版リポジトリとの関係

PHP 版 NENE2 の設計決定・ADR・フィールドトライアル記録は `../NENE2/docs/` を参照。
この Python 版は同じ原則に従い、Python のイディオムで実装する。

## 作業ガイドライン

- 詳細は `CLAUDE.md` を参照
- 変更は GitHub Issue ベースで進める
- `main` へ直接コミットしない
- PR 前に全チェックを通過させる
