# ADR-0001: ツールチェーン選定

- **Status**: Accepted
- **Date**: 2026-05-19

---

## Context

Python エコシステムには依存管理・Lint・型チェックのツールが乱立しており、プロジェクト初期に選定を固めないと後から変更コストが跳ね上がる。PHP 版 NENE2 で採用した「最先端の単一ツールで責務を明確に分担する」方針を Python にも適用する。

---

## Decision

### パッケージ管理: `uv`

- `pip` + `virtualenv` の組み合わせより圧倒的に速い（Rust 実装）
- `uv.lock` で完全再現性を保証
- `uv audit` / `pip-audit` で依存関係の脆弱性スキャンが容易
- **`pip`, `poetry`, `pipenv` は使用しない**

### Lint + Format: `ruff`

- `flake8` + `isort` + `pyupgrade` + `bandit` を一本化
- Rust 実装で高速、CI の待ち時間が最小
- セキュリティルール (`S` / bandit) も内包するため、`bandit` コマンドを別途実行しない
- **`flake8`, `pylint`, `black`, `isort` は使用しない**

有効化するルールセット:
| プレフィックス | 由来 | 目的 |
|---|---|---|
| E, W | pycodestyle | スタイル |
| F | pyflakes | 未使用変数・インポート |
| I | isort | インポート順序 |
| UP | pyupgrade | モダン Python 構文への自動アップグレード |
| ANN | flake8-annotations | 型注釈の強制 |
| N | pep8-naming | 命名規則 |
| B | flake8-bugbear | バグになりやすいパターン |
| SIM | flake8-simplify | 冗長なコードの簡略化 |
| S | flake8-bandit | セキュリティアンチパターン |
| T20 | flake8-print | `print()` 禁止 |
| PTH | flake8-use-pathlib | `os.path` 禁止 |
| RET | flake8-return | return 文の一貫性 |
| TRY | tryceratops | try-except のアンチパターン |
| PERF | perflint | パフォーマンスアンチパターン |
| PL | pylint | 包括的な品質チェック |
| LOG, G | flake8-logging | ロギングのアンチパターン |

### 型チェック: `mypy --strict`

- PHP 版 PHPStan level 8 相当
- `warn_unreachable = true` で到達不可能なコードを検出
- **`pyright`, `pytype` は使用しない**（mypy に一本化）

### テスト: `pytest`

- `pytest-asyncio` で非同期テスト対応
- `pytest-cov` でカバレッジ計測・80% 未満で CI 失敗
- **`unittest` は使用しない**

### 脆弱性スキャン: `pip-audit`

- CI の全チェックコマンドに含める
- CRITICAL / HIGH の CVE がある依存は PR マージ禁止

---

## Consequences

- ツールの追加・変更は ADR を書いてから行う
- 上記以外のツール（black, pylint, bandit コマンド等）の設定ファイルをコミットしない
- `pyproject.toml` がすべてのツール設定の唯一の置き場
