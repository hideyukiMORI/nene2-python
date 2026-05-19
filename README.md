# nene2-python

NENE2 の設計哲学を Python で実装したリファレンスフレームワーク。

[NENE2 (PHP)](https://github.com/hideyukiMORI/NENE2) と同一の原則を持ち、Python エコシステムに最適化している。

## 特徴

- **FastAPI + Pydantic v2** — モダン Python API スタック
- **クリーンアーキテクチャ** — UseCase / Domain を HTTP・DB から分離
- **mypy strict** — PHP 版 PHPStan level 8 相当の型安全性
- **ruff** — Lint + Format 一体型ツール
- **RFC 9457 Problem Details** — 統一エラーレスポンス
- **MCP 対応予定** — AI エージェントとのネイティブ統合

## 開発コマンド

```bash
uv sync                        # 依存インストール
uv run pytest                  # テスト
uv run mypy src/               # 型チェック
uv run ruff check src/ tests/  # Lint
uv run ruff format src/ tests/ # Format
uv run uvicorn src.example.app:app --reload --port 8080  # 開発サーバー
```

全チェック（CI と同等）:

```bash
uv run pytest && uv run mypy src/ && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/
```

## Docker

```bash
docker compose up app
curl http://localhost:8080/health
curl http://localhost:8080/notes
```

## PHP 版との対応

| PHP | Python |
|---|---|
| `readonly class` | `dataclass(frozen=True)` |
| `PHPStan level 8` | `mypy --strict` |
| `PHP-CS-Fixer` | `ruff format` |
| `composer check` | `uv run pytest && mypy && ruff` |
| `ValidationException` | `nene2.validation.ValidationException` |
| `PaginationQueryParser` | `nene2.http.PaginationQueryParser` |

## 関連リポジトリ

- [NENE2 (PHP)](https://github.com/hideyukiMORI/NENE2) — PHP リファレンス実装
