# Field Trial 44: PaginationQueryParser + PaginationResponse 実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.6 時点
**テーマ**: `PaginationQueryParser` を `Annotated[..., Depends()]` 構文で使い `PaginationResponse.to_dict()` でスロット付きデータクラスをシリアライズするパターンの実運用確認

---

## 概要

`PaginationQueryParser` を FastAPI の `Depends()` として注入し、
`PaginationResponse` + `to_dict()` でスロット付き `dataclass(frozen=True, slots=True)` を
シリアライズするパターンを実装した。
`total` フィールドのあり/なし両パターン、および生の dict アイテムを含むケースも確認した。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft44-pagination/` に以下を作成:

- **`app.py`** — `PaginationQueryParser` Depends 注入、スロット付きデータクラス `Product`、3 つのエンドポイント（total あり/なし/生 dict）
- **`test_app.py`** — デフォルト・カスタム・オフセット・total・スロット付きシリアライズ・422 (10 件)
- **`test_friction.py`** — 摩擦点の確認テスト (4 件)

**テスト結果**: 14 件全通過 ✅

---

## 摩擦点

### FP44-1: OpenAPI スキーマにクエリパラメータが正しく文書化される

**分類**: 摩擦なし（良い設計の確認）

`Annotated[PaginationQueryParser, Depends()]` 構文を使うと、
`Query(ge=1, le=100, description="Items per page (1–100)")` の情報が
FastAPI の自動 OpenAPI スキーマ生成に反映される。
`/openapi.json` の `parameters` に `limit`・`offset` が説明付きで表示される。

**判断**: FT10 で実装した `Depends()` 対応の効果が確認できた。

---

### FP44-2: PaginationResponse.to_dict() は元のアイテムを変更しない

**分類**: 摩擦なし（設計の確認）

`to_dict()` は `dataclasses.asdict()` で新しい dict を生成するため、
元の `dataclass` インスタンスは変更されない。immutable な `frozen=True` データクラスが
そのままリポジトリで保持できる。

---

### FP44-3: items が空リストのときも to_dict() が正常動作する

**分類**: 摩擦なし（エッジケース確認）

`items=[]` のとき `to_dict()` は `{"items": [], "limit": 20, "offset": 100, "total": 50}`
を返す。ページを超えたオフセットでのリクエストが自然に処理される。

---

### FP44-4: Depends() 使用時のバリデーションエラーが Problem Details 形式にならない

**分類**: 摩擦あり（Issues #268 で対応）

`PaginationQueryParser` を `Depends()` として使うと、
`limit=0` や `limit=101` のバリデーションは FastAPI が実行し、
エラーは FastAPI のデフォルト Pydantic 形式（`{"detail": [...]}`）になる:

```json
{"detail": [{"type": "greater_than_equal", ...}]}
```

一方、nene2 の `ValidationException` は Problem Details 形式:

```json
{"type": "...", "title": "Validation Failed", "status": 422, "errors": [...]}
```

この不一致を解消するため、`nene2.middleware.request_validation_error_handler` を
FastAPI の exception handler として登録することで Problem Details 形式に統一できる:

```python
from fastapi.exceptions import RequestValidationError
from nene2.middleware import request_validation_error_handler

app.add_exception_handler(RequestValidationError, request_validation_error_handler)
```

**対応**: `request_validation_error_handler` は `error_handler.py` に既存実装済みだったが、
`nene2.middleware` からエクスポートされていなかった (Issue #268)。
`nene2.middleware.__init__` に追加することで `from nene2.middleware import request_validation_error_handler` が可能になった。

---

## フレームワーク変更

- `nene2.middleware.__init__` に `request_validation_error_handler` を追加エクスポート (#268)

---

## 関連

- `nene2.http.PaginationQueryParser` (FT10, v1.3.0)
- `nene2.http.PaginationResponse` (FT10, v1.3.0)
- `nene2.middleware.request_validation_error_handler`
- FT10 (PaginationQueryParser Depends 対応, v1.3.0)
- Issue #268 (request_validation_error_handler エクスポート追加)
