# Field Trial 118: Python match 文パターンマッチング

## テーマ

Python 3.10+ の `match` 文を FastAPI アプリケーションのビジネスロジックで活用するパターンを検証する。
配送料計算・注文ステータス遷移・エラーコード分類を例に、データクラスパターン、OR パターン、ガード条件を検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft118-pattern-match/` に以下を実装:

- `calculate_shipping_fee()` — `ShippingAddress` dataclass に対するクラスパターンマッチ
- `get_next_status()` — `OrderStatus` StrEnum の OR パターンマッチ
- `classify_error()` — 整数リテラルとガード条件の組み合わせ
- 19 テスト通過

## テスト結果

全 19 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: dataclass のクラスパターンマッチで属性を同時に検査できる

```python
match address:
    case ShippingAddress(country="JP", express=False):
        return int(500 + weight_kg * 100)
    case ShippingAddress(country="JP", express=True):
        return int(1000 + weight_kg * 150)
    case ShippingAddress(country=country) if country in ("US", "CA", "AU"):
        return int(2000 + weight_kg * 300)
    case _:
        return int(3000 + weight_kg * 500)
```

`dataclass` フィールドを `case SomeClass(field=value):` で直接マッチできる。
ガード条件（`if country in (...)`）でリストメンバーシップも簡潔に書ける。

### O2: `StrEnum` の OR パターンで終端状態をまとめて処理できる

```python
match current:
    case OrderStatus.PENDING:
        return OrderStatus.CONFIRMED
    case OrderStatus.DELIVERED | OrderStatus.CANCELLED:
        return None  # 終端状態
```

`|` で複数の値をひとつの `case` にまとめられる。
`if-elif` よりも意図が明確で、追加した値が自動的に網羅性チェックに含まれる。

### O3: 整数ガードで範囲条件を表現できる

```python
match status_code:
    case 400:
        return "bad_request"
    case 401 | 403:
        return "auth_error"
    case code if 400 <= code < 500:
        return "client_error"
    case code if 500 <= code < 600:
        return "server_error"
    case _:
        return "unknown"
```

リテラルパターンを先に書き、ガード付きのキャプチャパターンをフォールバックにする設計が自然。
`if-elif` チェーンより意図が明確で、変数キャプチャ（`code`）と条件チェックを1行で書ける。

## まとめ

FT118 は摩擦ゼロ確認。`match` 文はビジネスロジックの分岐を型安全かつ可読性高く書ける。
CLAUDE.md の「パターンマッチ: `match` 文（長い `if-elif` 連鎖の禁止）」ポリシーと一致している。
