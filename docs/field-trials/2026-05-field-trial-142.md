# Field Trial 142: uuid モジュール

## テーマ

`uuid.uuid1〜uuid5` のバージョン別生成、名前空間定数、UUID パース・検証、
フォーマット変換、Pydantic モデルとの統合を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft142-uuid/` に以下を実装:

- `generate_uuid1()` — タイムスタンプ + MACアドレスベース (v1)
- `generate_uuid4()` — ランダム UUID (v4)
- `generate_uuid5()` — 名前空間 + SHA-1 ハッシュ (v5) — 決定論的
- `generate_uuid3()` — 名前空間 + MD5 ハッシュ (v3) — 決定論的（v5 推奨）
- `parse_uuid()` / `is_valid_uuid()` / `get_uuid_version()` — パース・検証
- `uuid_to_hex()` / `uuid_from_hex()` / `uuid_to_int()` / `uuid_from_int()` — フォーマット変換
- `generate_deterministic_id()` — 名前空間 DNS/URL/OID/X500 対応の v5 生成
- `EntityId` dataclass — 型安全な UUID ラッパー
- `ResourceBody` Pydantic モデルで `uuid.UUID` フィールドを検証
- 33 テスト通過（摩擦ゼロ）

## テスト結果

初回から 33 テスト全通過。

## Friction Points

なし。

## 観察

### O1: `uuid.UUID` は `int`, `hex`, `bytes` 等のキーワード引数でも生成できる

```python
value = uuid.UUID(int=some_128bit_int)   # 整数から生成
value = uuid.UUID(hex="abcdef...")       # ハイフンなし16進数から生成
value = uuid.UUID(bytes=b"\x00" * 16)   # 16バイトから生成
```

`parse_uuid(str)` だけでなく、整数・bytes からも相互変換できる。

### O2: `uuid.uuid5` / `uuid.uuid3` は同じ入力に対して常に同じ値を返す（決定論的）

```python
a = uuid.uuid5(uuid.NAMESPACE_URL, "https://example.com")
b = uuid.uuid5(uuid.NAMESPACE_URL, "https://example.com")
assert a == b  # True — 常に同じ

# 名前空間が違えば異なる UUID
c = uuid.uuid5(uuid.NAMESPACE_DNS, "https://example.com")
assert a != c  # True
```

リソース識別子を URL から決定論的に生成したい場合（冪等な ID 生成）に有効。
v3 は MD5 ベース（非推奨）、v5 は SHA-1 ベース（推奨）。

### O3: `uuid.UUID.version` でバージョン番号を確認できる

```python
v4 = uuid.uuid4()
assert v4.version == 4

v5 = uuid.uuid5(uuid.NAMESPACE_URL, "test")
assert v5.version == 5
```

ただし、`uuid.UUID` コンストラクタで文字列から作成した場合、
UUID フォーマットが valid であればバージョンに関係なく成功する点に注意。

### O4: Pydantic の `uuid.UUID` フィールドは自動で検証・変換される

```python
class ResourceBody(BaseModel):
    parent_id: uuid.UUID | None = Field(default=None)

# JSON 文字列を自動的に uuid.UUID にパースする
body = ResourceBody(**{"parent_id": "123e4567-e89b-12d3-a456-426614174000"})
assert isinstance(body.parent_id, uuid.UUID)
```

FastAPI のリクエストボディで `uuid.UUID` 型を使うと、
文字列の自動パースとバリデーションが行われる。

### O5: `uuid.NAMESPACE_DNS`, `NAMESPACE_URL`, `NAMESPACE_OID`, `NAMESPACE_X500` が標準で提供される

```python
uuid.NAMESPACE_DNS   # DNS 名（例: "python.org"）用名前空間
uuid.NAMESPACE_URL   # URL 用名前空間
uuid.NAMESPACE_OID   # ISO OID 用名前空間
uuid.NAMESPACE_X500  # X.500 DN 用名前空間
```

カスタム名前空間も `uuid.UUID("...")` で任意に定義できる。

## まとめ

FT142 は摩擦ゼロ。uuid モジュールは API が直感的で使いやすく、
FastAPI / Pydantic との統合もシームレスだった。
決定論的 ID 生成 (v5) が冪等な API 設計に有効であることを確認した。
