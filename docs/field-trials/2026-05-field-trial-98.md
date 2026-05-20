# Field Trial 98: PATCH / Partial Update パターン

**日付**: 2026-05-20
**テーマ**: Pydantic v2 の `exclude_unset=True` を使った部分更新パターン
**バージョン**: v1.8.31
**結果**: 摩擦あり（コード修正なし）

---

## 目的

HTTP PATCH で「送信されたフィールドのみ更新する」パターンを Pydantic v2 + nene2 で実装し、`None`（明示的 null）と「未送信」の区別ができることを検証する。

---

## 実施内容

`/home/xi/docker/nene2-python-FT/ft98-patch-partial-update/` に以下を実装:

- `app.py` — `PUT`（完全更新）と `PATCH`（部分更新）を持つユーザー CRUD
- 12 テスト（全 PASS）

---

## 確認できた良好な動作

### `exclude_unset=True` で未送信フィールドを除外

`PatchUserBody` の全フィールドを `Optional` にし、`model_dump(exclude_unset=True)` で送信されたフィールドだけを取り出す。

```python
class PatchUserBody(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=200)
    bio: str | None = Field(default=None, max_length=500)

@app.patch("/users/{user_id}")
def patch_user(user_id: int, body: PatchUserBody) -> JSONResponse:
    updates = body.model_dump(exclude_unset=True)
    updated = User(
        user_id=user_id,
        name=updates.get("name", current.name),
        email=updates.get("email", current.email),
        bio=updates.get("bio", current.bio),
    )
```

### `{}` と `{"bio": null}` を区別できる

`exclude_unset=True` により、空ボディ `{}` と `{"bio": null}` は正しく区別される。

```python
body_without_bio = PatchUserBody(name="Alice")
assert "bio" not in body_without_bio.model_dump(exclude_unset=True)  # 未送信
# {"bio": null} を送ると exclude_unset でも "bio" が含まれる → None に更新
```

---

## 摩擦点

### F98-1: PATCH ボディの全フィールドが Optional なため、バリデーションが緩くなる

`PUT` ボディは必須フィールドあり（空だと 422）。`PATCH` ボディは全フィールド Optional なため、空ボディ `{}` も有効に受け入れられる。

```python
# PUT: name 省略 → 422
client.put("/users/1", json={"email": "..."})  # 422

# PATCH: 全フィールド省略 → 200（空更新）
client.patch("/users/1", json={})  # 200（何も変わらない）
```

意図的な設計だが、API クライアント側が誤って空 PATCH を送っても検知できない。

### F98-2: `model_dump()` と `model_dump(exclude_unset=True)` の違いを意識する必要がある

`default=None` で定義したフィールドは、`model_dump()` では常に含まれる（`{"bio": None}`）。`exclude_unset=True` を忘れると「未送信」と「null 送信」の区別ができなくなる。

```python
# ❌ exclude_unset=True を忘れると未送信フィールドも含まれる
updates = body.model_dump()  # {"name": None, "email": None, "bio": None}

# ✅ 送信されたフィールドのみ
updates = body.model_dump(exclude_unset=True)  # {}
```

### F98-3: `str | None` フィールドで「クリアしたい」と「変更なし」が混同しやすい

`bio: str | None = None` の PATCH ボディでは、`{"bio": null}` が「bio を null にしたい」なのか「変更なし」なのかをクライアント側の意図だけで区別する必要がある。`exclude_unset=True` により `{"bio": null}` は「null に更新」として正しく扱えるが、API ドキュメントでこの挙動を明記する必要がある。

---

## 結論

Pydantic v2 の `exclude_unset=True` + 全フィールド `Optional` の PATCH パターンは nene2 と問題なく組み合わせられる。
主な摩擦はバリデーションの緩さと `model_dump` の使い分け。コード修正は不要。
