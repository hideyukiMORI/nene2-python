# Field Trial 132: __init_subclass__ + クラスデコレーター

## テーマ

`__init_subclass__` でサブクラスを自動登録するプラグインシステムと、
クラスデコレーターでメソッドを注入するパターンを FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft132-init-subclass/` に以下を実装:

- `PaymentMethod` 基底クラス — `__init_subclass__(*, method_name="")` でサブクラスを `_payment_registry` に自動登録
- `CreditCardPayment`, `PayPalPayment`, `BankTransferPayment` — キーワード引数で名前を指定してサブクラス登録
- `add_audit_log()` — クラスデコレーター: `to_audit_log()` メソッドを注入
- `validate_positive_fields()` — デコレーターファクトリ: 指定フィールドの正値バリデーションを `__init__` に追加
- `OrderItem` — 両デコレーターを適用したクラス
- `GET /payment-methods` — 登録済み決済方法一覧
- `POST /pay/{method}` — プラグイン経由で決済処理
- `POST /order-items` — バリデーション付き注文明細作成
- 17 テスト通過

## テスト結果

全 17 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `__init_subclass__` でサブクラスが定義時に自動登録される

```python
_payment_registry: dict[str, type[PaymentMethod]] = {}

class PaymentMethod:
    def __init_subclass__(cls, *, method_name: str = "", **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if method_name:
            cls.name = method_name
            _payment_registry[method_name] = cls

class CreditCardPayment(PaymentMethod, method_name="credit_card"):
    ...

# クラス定義時に自動で _payment_registry["credit_card"] = CreditCardPayment が実行される
```

`__init_subclass__` はクラス定義時（モジュールのインポート時）に呼ばれる。
プラグインファイルをインポートするだけで登録が完了するため、
レジストリへの明示的な登録コードが不要になる。

### O2: クラスデコレーターでメソッドを後付けで注入できる

```python
def add_audit_log(cls: type) -> type:
    def to_audit_log(self: object) -> dict[str, object]:
        return {"class": type(self).__name__, "fields": {...}}
    cls.to_audit_log = to_audit_log
    return cls

@add_audit_log
class OrderItem: ...

item.to_audit_log()  # 注入されたメソッドが使える
```

クラスデコレーターはクラスオブジェクトを受け取って変換するため、
複数のクラスに共通の機能を後付けするのに適している。

### O3: デコレーターファクトリで `__init__` を動的に拡張できる

```python
def validate_positive_fields(*field_names: str) -> Callable[[type], type]:
    def decorator(cls: type) -> type:
        original_init = cls.__init__

        def new_init(self: object, *args: object, **kwargs: object) -> None:
            original_init(self, *args, **kwargs)
            for field in field_names:
                value = getattr(self, field, None)
                if value is not None and isinstance(value, (int, float)) and value <= 0:
                    raise ValueError(f"{field} must be positive, got {value}")

        cls.__init__ = new_init
        return cls
    return decorator
```

元の `__init__` を保持して新しい `__init__` でラップするため、
既存の初期化ロジックを壊さずにバリデーションを追加できる。

## まとめ

FT132 は摩擦ゼロ確認。`__init_subclass__` によるプラグイン自動登録と
クラスデコレーターによるメソッド注入・`__init__` 拡張を確認した。
`__init_subclass__` はプラグインアーキテクチャの実装として有用。
