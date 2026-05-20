# Field Trial 148: json 高度機能

## テーマ

`json.JSONEncoder` サブクラス, `object_hook`, `object_pairs_hook`,
カスタムシリアライズ/デシリアライズを FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft148-json-advanced/` に以下を実装:

- `ExtendedEncoder` — `json.JSONEncoder` サブクラスで `datetime`/`date`/`Decimal`/`UUID` を `{"__type__": "...", "value": "..."}` 形式にシリアライズ
- `extended_object_hook` — `__type__` フィールドを見て Python オブジェクトを復元するデコーダー（`match` 文を活用）
- `extended_dumps` / `extended_loads` — `ExtendedEncoder` と `extended_object_hook` を組み合わせたラッパー関数
- `Event` ドメインオブジェクト — `uuid.UUID` / `datetime` / `Decimal` を持つ `dataclass` のラウンドトリップ確認
- `validate_json_structure` — `{"field": "type_name"}` 形式の簡易スキーマ検証
- `json_diff` — 2つの JSON オブジェクトの差分（added / removed / changed）を返す
- HTTP エンドポイント 3 本 (`/json/serialize-event`, `/json/validate`, `/json/diff`)
- 24 テスト全通過（摩擦0件）

## テスト結果

初回: 24 テスト全通過（1 warning — Pydantic が `schema` フィールド名に対して発する UserWarning、テスト自体は影響なし）。

## 摩擦なし

今回はブロッカーとなる摩擦なし。`match` 文を型ディスパッチに使うと可読性が向上した。

## 観察

### O1: `json.JSONEncoder.default()` は標準型以外のオブジェクトに対して呼ばれる

```python
class ExtendedEncoder(json.JSONEncoder):
    def default(self, obj: object) -> object:
        if isinstance(obj, datetime):
            return {"__type__": "datetime", "value": obj.isoformat()}
        if isinstance(obj, Decimal):
            return {"__type__": "decimal", "value": str(obj)}
        if isinstance(obj, uuid.UUID):
            return {"__type__": "uuid", "value": str(obj)}
        return super().default(obj)  # 不明な型は TypeError を送出
```

`default()` の戻り値はそのまま JSON に埋め込まれる。
辞書を返せばネストした JSON オブジェクトになる。
`datetime` は `date` のサブクラスなので、`isinstance` チェックは `datetime` を先に行う。

### O2: `object_hook` はすべての JSON オブジェクトに適用される

```python
def extended_object_hook(obj: dict[str, Any]) -> Any:
    if "__type__" not in obj:
        return obj  # 通常オブジェクトはそのまま返す
    match obj["__type__"]:
        case "datetime":
            return datetime.fromisoformat(obj["value"])
        case "decimal":
            return Decimal(obj["value"])
        case "uuid":
            return uuid.UUID(obj["value"])
        case _:
            return obj  # 不明な __type__ はそのまま返す
```

`object_hook` はネストしたオブジェクトに対してもボトムアップで再帰的に呼ばれる。
`match` 文を使うと `if-elif` 連鎖より可読性が高い。

### O3: `datetime` のラウンドトリップには timezone-aware が必要

```python
now = datetime(2026, 5, 21, 10, 30, 0, tzinfo=UTC)
serialized = extended_dumps({"ts": now})
# → {"ts": {"__type__": "datetime", "value": "2026-05-21T10:30:00+00:00"}}
restored = extended_loads(serialized)
assert restored["ts"] == now  # ✅
```

`datetime.isoformat()` はタイムゾーン情報を保持し、
`datetime.fromisoformat()` は `+00:00` を正しく解釈して `UTC` タイムゾーンで復元する。

### O4: `object_pairs_hook` は重複キーの処理に使える

```python
def load_with_duplicate_keys(text: str) -> list[tuple[str, Any]]:
    """重複キーを保持したまま JSON を読み込む。"""
    pairs: list[tuple[str, Any]] = []
    json.loads(text, object_pairs_hook=lambda items: pairs.extend(items) or dict(items))
    return pairs
```

`object_pairs_hook` はキー・値ペアのリストを受け取るため、
重複キーを失わずにすべてのペアを収集できる。
`object_hook` と `object_pairs_hook` は同時指定不可（後者が優先）。

### O5: `json_diff` で JSON オブジェクトの変更を追跡できる

```python
diff = json_diff({"a": 1, "b": 2}, {"a": 99, "c": 3})
# → {"added": {"c": 3}, "removed": {"b": 2}, "changed": {"a": {"from": 1, "to": 99}}}
```

辞書のセット演算（`set(a) & set(b)` 等）で追加・削除・変更を分類できる。

## まとめ

FT148 は摩擦ゼロ。`json.JSONEncoder` サブクラスと `object_hook` で
非標準型の完全なシリアライズ/デシリアライズラウンドトリップを実現できた。
Python 3.12 の `match` 文が型ディスパッチのコードを簡潔にした。
