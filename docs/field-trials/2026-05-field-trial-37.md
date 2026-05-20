# Field Trial 37: PaginationResponse + PaginationQueryParser 実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.4 時点
**テーマ**: `PaginationQueryParser` の `Depends()` パターンと `PaginationResponse.to_dict()` を使ったページネーションパイプラインの実運用確認

---

## 概要

50 件の `Product` データを `PaginationQueryParser` で limit/offset 制御し、
`PaginationResponse.to_dict()` で slotted dataclass を自動シリアライズして `JSONResponse` に変換するパイプラインを検証した。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft37-pagination/` に以下を作成:

- **`app.py`** — `Annotated[PaginationQueryParser, Depends()]` パターンの `/api/products` エンドポイント
- **`test_app.py`** — デフォルト・カスタム・最終ページ・無効値・Depends 動作確認 (9 件)
- **`test_friction.py`** — 摩擦点の確認テスト (4 件)

**テスト結果**: 13 件全通過 ✅

---

## 摩擦点

### FP37-1: `Annotated[PaginationQueryParser, Depends()]` と書く必要がある

**分類**: 軽微な摩擦（FastAPI 標準パターン）

`def list(pagination: PaginationQueryParser = Depends())` ではなく
`def list(pagination: Annotated[PaginationQueryParser, Depends()])` が推奨パターン。
FastAPI の仕様に従っているが、初見では迷いやすい。

**判断**: `docs/how-to/validation.md` および新規作成する how-to への記載で対応。

---

### FP37-2: `to_dict()` は dataclass のみ自動シリアライズ

**分類**: 既知の制約（軽微）

`PaginationResponse.to_dict()` は `dataclasses.is_dataclass()` で判定する。
Pydantic モデルの items は `.model_dump()` を個別に呼ぶ必要がある。
通常の dict はそのまま通過する。

**判断**: dataclass 向け最適化という設計意図通り。
Pydantic モデルとの混在ユースケースは how-to ドキュメントに記載する。

---

### FP37-3: `total` 省略時に `"total"` キーが消える（設計通り）

**分類**: 設計通り（摩擦なし）

`PaginationResponse(items=[], limit=10, offset=0)` のように `total` を渡さないと
`to_dict()` の結果に `"total"` キーが含まれない。
`total=None` を明示しても同じ結果。

**判断**: 全件数を取得しない効率的なページネーションをサポートする意図通り。

---

## フレームワーク変更

なし（全て設計通りの挙動）

---

## 関連

- `nene2.http.PaginationQueryParser`
- `nene2.http.PaginationResponse`
- FT10 (PaginationResponse.to_dict() スロット対応, v1.3.0)
