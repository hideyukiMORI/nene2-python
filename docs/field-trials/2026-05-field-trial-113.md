# Field Trial 113: Pydantic 識別共用体（Discriminated Union）

## テーマ

`Literal` 型 + `Field(discriminator="type")` による Pydantic v2 の識別共用体パターンを検証する。
異なる形状を持つペイロードを 1 つの Union 型で受け取り、OpenAPI スキーマに oneOf として反映させる。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft113-discriminated-union/` に以下を実装:

- `TextEvent`, `ImageEvent`, `VideoEvent` — それぞれ `type: Literal["text" | "image" | "video"]` を持つ Pydantic モデル
- `Event = Annotated[Union[TextEvent, ImageEvent, VideoEvent], Field(discriminator="type")]`
- `POST /events` — 識別共用体でリクエストを受け取り、型を自動判別
- `GET /events` — クエリパラメータ `event_type` でフィルタリング
- 10 テスト通過

## テスト結果

全 10 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `Field(discriminator="type")` で識別共用体を定義できる

```python
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field

class TextEvent(BaseModel):
    type: Literal["text"]
    content: str

class ImageEvent(BaseModel):
    type: Literal["image"]
    url: str

Event = Annotated[
    Union[TextEvent, ImageEvent],
    Field(discriminator="type"),
]

class EventRequest(BaseModel):
    event: Event
```

`{"type": "text", "content": "Hello"}` → `TextEvent` に自動マッピングされる。
未知の `type` 値（`"audio"` など）は 422 になる。

### O2: OpenAPI スキーマに `oneOf` + `discriminator` が反映される

FastAPI の `/docs` で確認すると、リクエストボディのスキーマが以下のように生成される:

```json
{
  "oneOf": [
    { "$ref": "#/components/schemas/TextEvent" },
    { "$ref": "#/components/schemas/ImageEvent" },
    { "$ref": "#/components/schemas/VideoEvent" }
  ],
  "discriminator": { "propertyName": "type" }
}
```

各サブモデルのスキーマも個別に定義され、OpenAPI クライアントが型を正確に認識できる。

### O3: 必須フィールドの欠如・型ミスマッチは 422 になる

識別子 `type` が合致してもサブモデルのバリデーションは完全に行われる。
`{"type": "text"}` （`content` 欠如）や `{"type": "video", "duration_seconds": -1}` は 422 になる。

## まとめ

FT113 は摩擦ゼロ確認。Pydantic v2 の識別共用体は `Field(discriminator="type")` + `Literal` で
簡潔に実装でき、OpenAPI スキーマにも正確に反映される。
