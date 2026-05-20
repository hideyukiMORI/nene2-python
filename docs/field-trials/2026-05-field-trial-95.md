# Field Trial 95: Pydantic `model_validator` / `field_validator` と nene2 統合

**日付**: 2026-05-20
**テーマ**: Pydantic カスタムバリデーターと nene2 ValidationException の統合
**バージョン**: v1.8.30
**結果**: 摩擦あり（コード修正なし）

---

## 目的

`@field_validator` / `@model_validator` を使ったカスタムバリデーションが、nene2 の ValidationException を通じて 422 Problem Details としてどのように表現されるかを検証する。

---

## 実施内容

`/home/xi/docker/nene2-python-FT/ft95-pydantic-validators/` に以下を実装:

- `app.py` — `@field_validator`（単フィールド変換・検証）+ `@model_validator(mode="after")`（クロスフィールド検証）
- 10 テスト（全 PASS）

---

## 確認できた良好な動作

### `@field_validator` のエラーは正しいフィールド名を持つ

`@field_validator("username")` で `raise ValueError(...)` すると、nene2 の 422 レスポンスの `errors[].field` に `"username"` が入る。

```python
{
  "errors": [
    {
      "field": "username",
      "message": "Value error, Username must not contain spaces",
      "code": "value_error"
    }
  ]
}
```

### 複数フィールドエラーの集約

複数フィールドで同時にバリデーションエラーが発生した場合、`errors` 配列にすべて集約される。

```json
{
  "errors": [
    {"field": "username", "message": "..."},
    {"field": "email", "message": "..."}
  ]
}
```

### `@field_validator` の値変換（`lower()` など）

`@field_validator` で値を変換して返すと、`@model_validator(mode="after")` には変換後の値が渡される。

---

## 摩擦点

### F95-1: `@model_validator(mode="after")` のエラーは `field: "request"`

`@model_validator` は特定フィールドに紐付かないため、nene2 の ValidationException 変換では `loc` が空タプル `()` になる。nene2 の `_loc_to_field()` はこれを `"request"` に変換する。

```python
@model_validator(mode="after")
def passwords_match(self) -> Self:
    if self.password != self.password_confirm:
        raise ValueError("Passwords do not match")
    return self
```

実際のレスポンス:
```json
{
  "errors": [
    {
      "field": "request",
      "message": "Value error, Passwords do not match",
      "code": "value_error"
    }
  ]
}
```

**対処法**: フロントエンドでは `field: "request"` はフォーム全体に対するエラーとして扱い、特定フィールドには紐付けない。クロスフィールドバリデーションエラーのメッセージは具体的に書く（どのフィールドが問題かを文言に含める）。

### F95-2: `@model_validator` の `mode="before"` と `mode="after"` の実行順序

- `mode="before"` → raw dict に対して実行（`@field_validator` より前）
- `mode="after"` → 全 `@field_validator` 実行後に実行

クロスフィールドバリデーションには `mode="after"` を使うのが正しいが、`@field_validator` が `raise ValueError` した場合、そのフィールドは `None` またはデフォルト値になりうるため、`mode="after"` の model_validator 内でのアクセスに注意が必要。

### F95-3: `@field_validator` の値変換はテストで検証しにくい

`@field_validator` で `value.lower()` などの変換を行うと、バリデーションとは別に変換の副作用がある。テスト時にレスポンスの値が元の入力と異なることに気づきにくい。

```python
@field_validator("username")
@classmethod
def username_no_spaces(cls, value: str) -> str:
    if " " in value:
        raise ValueError("...")
    return value.lower()  # ← 変換している

# テストで元の値 "Alice" が "alice" になることを確認しないと気づかない
r = client.post("/register", json={"username": "Alice", ...})
assert r.json()["username"] == "alice"  # ← 変換後の値
```

---

## 結論

`@field_validator` / `@model_validator` は nene2 の 422 Problem Details と問題なく統合できる。
主な摩擦は `@model_validator` エラーの `field: "request"` 表現と、`mode="before"/"after"` の実行順序の把握。
コード修正は不要で、パターンの理解で対応できる。
