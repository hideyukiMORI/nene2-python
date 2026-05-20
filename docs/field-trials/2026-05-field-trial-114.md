# Field Trial 114: プラグインレジストリパターン

## テーマ

`@runtime_checkable Protocol` + 辞書ベースのレジストリで、型安全なプラグイン登録・ディスパッチを実現するパターンを検証する。
通知ハンドラー（email / slack / webhook）を例に、実行時の `isinstance` チェックと OpenAPI ルーティングを組み合わせる。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft114-plugin-registry/` に以下を実装:

- `NotificationHandlerProtocol` — `@runtime_checkable Protocol`（`name: str` + `handle()` メソッド）
- `_registry: dict[str, NotificationHandlerProtocol]` — モジュールレベルのレジストリ
- `register_handler()` / `get_handler()` / `list_handlers()` — レジストリ操作関数
- `EmailHandler`, `SlackHandler`, `WebhookHandler` — 組み込みハンドラー（Protocol を満たすが継承しない）
- `POST /notify` — ハンドラー名でディスパッチ
- `GET /handlers` — 登録済みハンドラー一覧
- 9 テスト通過

## テスト結果

全 9 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `@runtime_checkable Protocol` で isinstance チェックが使える

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class NotificationHandlerProtocol(Protocol):
    name: str
    def handle(self, payload: dict[str, object]) -> dict[str, object]: ...

assert isinstance(EmailHandler(), NotificationHandlerProtocol)  # True
```

継承なしに Protocol を満たす任意のクラスを `isinstance` で検証できる。
レジストリに登録する前の型チェックに使えるが、属性の実行時チェックはメソッド定義の存在のみ確認する（引数型は確認されない）。

### O2: モジュールレベル辞書レジストリは test fixture でリセット可能

```python
_registry: dict[str, NotificationHandlerProtocol] = {}

@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    _registry.clear()
    register_handler(EmailHandler())
    ...
```

モジュールグローバルの辞書を直接 `clear()` → 再登録することでテスト間の独立性を確保できる。
`importlib.reload()` は不要。

### O3: 構造的サブタイピングでサードパーティハンドラーが差し込める

Protocol を使うため、外部パッケージのクラスでも `name` と `handle()` があれば登録できる。
ABC 継承を強制しないため、既存コードへの侵食がない。

## まとめ

FT114 は摩擦ゼロ確認。`@runtime_checkable Protocol` + 辞書レジストリは、
拡張性の高いプラグインシステムを最小コードで実現できる。
