# Field Trial 135: abc モジュール + 抽象基底クラス

## テーマ

`ABC`, `abstractmethod`, `abstractproperty` を使ったインターフェース定義と
テンプレートメソッドパターン、リポジトリパターンを FastAPI で検証する。
Protocol との使い分けも含めて確認する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft135-abc-interface/` に以下を実装:

- `NotificationServiceInterface(ABC)` — `send`, `get_channel`, `max_message_length` を抽象定義
- テンプレートメソッド `send_truncated()` — ABC で共通ロジックを提供
- `EmailNotification`, `SlackNotification`, `SmsNotification` — 具体実装
- `ItemRepositoryInterface(ABC)` — CRUD の抽象インターフェース
- `InMemoryItemRepository` — テスト用インメモリ実装
- 通知送信・リポジトリ CRUD の HTTP エンドポイント
- 21 テスト通過

## テスト結果

全 21 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: 抽象クラスは `__abstractmethods__` が空でないとインスタンス化できない

```python
class NotificationServiceInterface(ABC):
    @abstractmethod
    def send(self, recipient: str, message: str) -> bool: ...

NotificationServiceInterface()  # TypeError: Can't instantiate abstract class
```

すべての `@abstractmethod` を実装してはじめてインスタンス化できる。
実装漏れを実行時に確実に検出できる。

### O2: `@property` + `@abstractmethod` で抽象プロパティを定義できる

```python
@property
@abstractmethod
def max_message_length(self) -> int: ...
```

デコレーターの順序は `@property` が外側（上）、`@abstractmethod` が内側（下）。
サブクラスでは通常の `@property` で実装する。

### O3: テンプレートメソッドパターンで共通ロジックを ABC に持てる

```python
class NotificationServiceInterface(ABC):
    @abstractmethod
    def send(self, recipient: str, message: str) -> bool: ...

    def send_truncated(self, recipient: str, message: str) -> bool:
        truncated = message[:self.max_message_length]
        return self.send(recipient, truncated)  # 抽象メソッドを呼ぶ
```

ABC でも具体的なメソッドを持てる。サブクラスは `send` のみ実装すれば
`send_truncated` の共通ロジックを継承できる。

### O4: ABC vs Protocol の使い分け

| 特性 | ABC | Protocol |
|---|---|---|
| 実装の強制 | ✅ `TypeError` でインスタンス化失敗 | ❌（`@runtime_checkable` でも実行時チェックは型のみ） |
| 継承の必要性 | ✅ 継承必須 | ❌ 構造的サブタイピング（継承不要） |
| テンプレートメソッド | ✅ ABC に具体的メソッドを持てる | ❌（Protocol は型定義のみ） |
| `isinstance` チェック | ✅ `isinstance(obj, Interface)` | ✅ `@runtime_checkable` で可能 |
| 外部ライブラリへの適用 | ❌ 継承が必要 | ✅ 既存クラスでも適合 |

nene2-python の方針: `Protocol` を優先（構造的サブタイピング）、共通実装が必要な場合のみ `ABC`。

## まとめ

FT135 は摩擦ゼロ確認。`ABC` によるインターフェース定義と
テンプレートメソッドパターンの組み合わせを確認した。
CLAUDE.md では `Protocol` を主として推奨しているが、テンプレートメソッドが必要な場合は
`ABC` の選択が妥当であることを確認した。
