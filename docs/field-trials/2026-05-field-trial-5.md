# Field Trial 5 — wallet: transactional() DX 検証

## Date

2026-05-19

## Baseline

- nene2-python v0.1.0 (`uv add git+https://github.com/hideyukiMORI/nene2-python.git`)
- Python 3.14.5（uv managed）
- プロジェクト: **wallet** — ウォレット送金 JSON API
- エンティティ: `Account`（id, name, balance_cents）、`Transfer`（id, from/to, amount_cents）
- 5 エンドポイント（GET/POST accounts, POST transfer, GET transfers）
- **`SqlAlchemyTransactionManager.transactional()`** ← FT1〜FT4 で未検証のコア機能

## Goal

1. `transactional()` コールバックパターンの実用 DX を確認する
2. `transactional()` と Repository パターンの組み合わせ方を検証する
3. 原子性（失敗時ロールバック）が実際に機能することを確認する

---

## Steps Taken

### 1. プロジェクト初期化・インストール

問題なし。FT1〜FT4 で確立されたパターン通り。

### 2. `_in_tx` パターンの設計

`transactional()` コールバック内でリポジトリ操作を行うため、executor を受け取る専用メソッドを定義した（**F-2**）：

```python
class AccountRepositoryInterface(ABC):
    def find_by_id(self, account_id: int) -> Account | None: ...

    # トランザクション内専用 — transactional() コールバック内から呼ぶ
    def find_by_id_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int
    ) -> Account | None: ...
    def update_balance_in_tx(
        self, executor: DatabaseQueryExecutorInterface, account_id: int, delta_cents: int
    ) -> None: ...
```

UseCase での使い方：

```python
class TransferUseCase:
    def execute(self, input_: TransferInput) -> Transfer:
        def _run(executor: DatabaseQueryExecutorInterface) -> Transfer:
            source = self._accounts.find_by_id_in_tx(executor, input_.from_account_id)
            if source is None:
                raise AccountNotFoundException(input_.from_account_id)
            target = self._accounts.find_by_id_in_tx(executor, input_.to_account_id)
            if target is None:
                raise AccountNotFoundException(input_.to_account_id)
            if source.balance_cents < input_.amount_cents:
                raise InsufficientBalanceException(...)

            self._accounts.update_balance_in_tx(executor, input_.from_account_id, -input_.amount_cents)
            self._accounts.update_balance_in_tx(executor, input_.to_account_id, input_.amount_cents)
            return self._transfers.create_in_tx(executor, ...)

        return self._tx.transactional(_run)
```

### 3. transactional() 動作確認

```
POST /accounts  {"name": "Alice", "initial_balance_cents": 10000}  → 201
POST /accounts  {"name": "Bob",   "initial_balance_cents": 5000}   → 201
POST /accounts/1/transfer  {"to_account_id": 2, "amount_cents": 3000}  → 201
GET  /accounts/1  → balance_cents: 7000  ✓ (10000 - 3000)
GET  /accounts/2  → balance_cents: 8000  ✓ (5000 + 3000)
```

### 4. 原子性の確認

存在しない転送先を指定 → Alice の残高が変わらないことを確認：

```
POST /accounts/1/transfer  {"to_account_id": 9999, "amount_cents": 1000}  → 404
GET  /accounts/1  → balance_cents: 7000  ✓ (変化なし = ロールバック成功)
```

`engine.begin()` コンテキストマネージャーが例外で自動ロールバックすることを実証。

### 5. エラーレスポンス確認

```
POST /accounts/1/transfer  {"amount_cents": 9999}  （残高 7000 に対して）
→ 422 {"type": ".../insufficient-balance", "title": "Insufficient Balance", ...}  ✓
```

### 6. mypy 実行（F-1 発見）

```
Skipping analyzing "nene2.http": module is installed, but missing library stubs or py.typed marker
```

`ignore_missing_imports = true` + `warn_return_any = false` で回避。詳細は F-1 参照。

---

## Friction Points

### F-1 nene2-python に py.typed マーカーがなく型情報が失われる

**severity**: 中
**type**: パッケージ設定不備

`uv run mypy src/` を実行すると nene2 モジュールの型情報が読み込まれない。
PEP 561 の `py.typed` マーカーファイルが `src/nene2/` に存在しないため。

回避策として以下を `[tool.mypy]` に追加した：
```toml
ignore_missing_imports = true
warn_return_any = false
```

本来これらは不要なはず。nene2 には型注釈が完備されており、`py.typed` を追加するだけで解決する。

**Follow-up**: `src/nene2/py.typed` を追加して PEP 561 対応する。

### F-2 transactional() とリポジトリを組み合わせるパターンがドキュメントなし

**severity**: 中
**type**: ドキュメント不足

`transactional(callback)` でコールバック内からリポジトリを呼ぶ方法が非自明。
実装してみると「`_in_tx` サフィックス付きメソッドで executor を受け取る」パターンが自然だと分かったが、ガイドがない。

**Follow-up**: `docs/reference/framework-modules.md` と `docs/how-to/sqlalchemy-repository.md` に `transactional()` 実践パターンを追記する。

---

## Summary

| ID  | 摩擦                                                         | 深刻度 | 種別             | Follow-up Issue |
|-----|--------------------------------------------------------------|--------|------------------|-----------------|
| F-1 | `py.typed` マーカーなしで mypy 型情報が失われる              | 中     | パッケージ設定   | #94             |
| F-2 | `transactional()` + リポジトリの `_in_tx` パターンが非文書化 | 中     | ドキュメント不足 | #95             |

`transactional()` 自体は設計通り動作し、原子性も確認。
`_in_tx` パターンは一度設計すると明快で、InMemory 実装でも再現しやすい（テスト容易性◎）。

次回 FT6 は以下のいずれかを推奨：
- F-1/F-2 修正後に **PyPI 公開フロー**の検証
- WebSocket サポートの検討（FastAPI の WebSocket エンドポイントをフレームワーク観点で評価）
