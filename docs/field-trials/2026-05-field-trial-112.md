# Field Trial 112: バルクアップデートパターン（PATCH /items/bulk）

## テーマ

FT107（バルク作成・削除）の応用として、PATCH による一括更新操作を検証する。
- 部分更新（name のみ、price のみ、両方）
- 207 Multi-Status で部分成功/失敗
- `dataclasses.replace()` でイミュータブルエンティティを更新

## 実施内容

`/home/xi/docker/nene2-python-FT/ft112-bulk-update/` に以下を実装:

- `PATCH /items/bulk` — 一括更新（部分成功対応）
- `ItemUpdateRequest` — `name: str | None`, `price: int | None`（両方省略可能、一方だけ指定可能）
- `@field_validator` でカスタムバリデーション（空白名チェック）
- `dataclasses.replace()` でフィールドを選択的に更新
- 8 テスト通過

## テスト結果

全 8 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: PATCH の部分更新は `name: str | None = None` + `dataclasses.replace()` で実現

```python
class ItemUpdateRequest(BaseModel):
    item_id: int
    name: str | None = None  # 省略可
    price: int | None = None  # 省略可

new_name = update.name if update.name is not None else item.name
new_price = update.price if update.price is not None else item.price
updated = replace(item, name=new_name, price=new_price)
```

`None` をデフォルトにすることで「指定されたフィールドのみ更新」を表現できる。

### O2: `@field_validator` でフィールドレベルのカスタムバリデーションが簡単

```python
@field_validator("name")
@classmethod
def name_must_not_be_empty(cls, v: str | None) -> str | None:
    if v is not None and v.strip() == "":
        raise ValueError("name must not be empty")
    return v
```

`None` の場合はスキップし、空白文字のみの文字列を拒否する設計が自然に書ける。

### O3: バルク更新とバルク作成・削除のパターンは統一できる

FT107（バルク作成・削除）と同じ 207 Multi-Status パターンで一括更新を実装できた。
`succeeded` / `failed` / `total` の構造を一貫させることでクライアント側の処理が統一できる。

## まとめ

FT112 は摩擦ゼロ確認。PATCH バルク更新は既存の 207 パターン + `dataclasses.replace()` で実現できる。
