# Field Trial 109: API バージョニング（v1/v2 ルーティング）

## テーマ

FastAPI の `APIRouter` を使って `/v1` と `/v2` でエンドポイントを分離するパターンを検証する。
- フィールド名の変更（`email` → `contact_email`）
- フィールドの追加（`age` を v2 で追加）
- `full_name` から `first_name`/`last_name` への分割
- OpenAPI スキーマが両バージョンを正確に反映するか

## 実施内容

`/home/xi/docker/nene2-python-FT/ft109-api-versioning/` に以下を実装:

- ドメイン `User` dataclass（バージョン非依存）
- `UserResponseV1` — `full_name`, `email`
- `UserResponseV2` — `first_name`, `last_name`, `contact_email`, `age`
- `v1_router = APIRouter(prefix="/v1", tags=["v1"])`
- `v2_router = APIRouter(prefix="/v2", tags=["v2"])`
- 9 テスト通過

## テスト結果

全 9 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。`APIRouter(prefix="/v1")` でルーターを分離し `app.include_router()` で登録するだけで
バージョン分離が完成する。OpenAPI スキーマも `UserResponseV1` / `UserResponseV2` を
個別に定義することで両バージョンのスキーマが正確に生成される。

## 観察

### O1: バージョン間の共有ロジックはドメイン層に置く

`find_user()` などのクエリ関数はバージョン非依存のドメイン層に置き、
各バージョンのハンドラーから呼ぶ設計が自然に機能した。
`from_domain()` クラスメソッドで変換することでドメインと HTTP を分離できた。

### O2: OpenAPI タグでバージョンを整理できる

`tags=["v1"]` / `tags=["v2"]` を `APIRouter` に指定すると、
Swagger UI でバージョンごとにグループ化されて見やすくなる。

### O3: `APIRouter` prefix は重複しない

`app.include_router(v1_router)` で登録すると `/v1/users` になる。
ルーター内のパスに `/v1` を書く必要はない（二重にならない）。

## まとめ

FT109 は摩擦ゼロ確認。APIバージョニングは FastAPI の `APIRouter` + `prefix` で
自然に実現できる。how-to ドキュメントに記録のみ。
