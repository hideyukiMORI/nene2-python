# FT25: RequestIdMiddleware 実運用検証

**日付**: 2026-05-20
**テーマ**: `RequestIdMiddleware` のリクエスト ID 生成・伝播・ContextVar 統合の実運用検証
**FT アプリ**: `/home/xi/docker/nene2-python-FT/ft25-request-id/`

---

## 目的

`nene2.middleware.RequestIdMiddleware` と `request_id_var` を使って、
リクエスト ID を生成・伝播するパターンを検証する。

---

## 実施内容

- `/api/echo` エンドポイントで `request_id_var.get()` を返す
- クライアント提供の有効 UUID v4 の伝播確認
- 無効な ID が新しい UUID に置き換えられることを確認

---

## テスト結果

### test_app.py（正常系・機能確認）
| テスト | 結果 |
|---|---|
| test_response_includes_x_request_id_header | PASS |
| test_request_id_is_available_in_handler | PASS |
| test_client_supplied_valid_uuid_is_preserved | PASS |
| test_client_supplied_invalid_id_is_replaced | PASS |
| test_each_request_gets_unique_id | PASS |

### test_friction.py（摩擦点確認）
| テスト | 結果 | 摩擦 |
|---|---|---|
| test_request_id_not_accessible_from_middleware_stack | PASS | あり（ドキュメント） |
| test_no_helper_to_get_request_id_from_header_in_handler | PASS | あり |
| test_request_id_contextvars_isolation_per_request | PASS | なし（正しい動作） |

---

## 発見した摩擦点

### FT25-F1: ミドルウェア順序依存がドキュメントに明記されていない

**概要**: `request_id_var` はミドルウェアの実行順序に依存するが、
これがドキュメントに明記されていない。
`RequestIdMiddleware` より先に実行されるミドルウェアでは `request_id_var.get()` が空になる。

**判断**: ミドルウェア追加順のドキュメント化で対応（how-to に記載）。

---

### FT25-F2: FastAPI Depends 用の get_request_id() ヘルパーがない

**概要**: `request_id_var.get()` で直接取得できるが、
FastAPI の依存性注入パターンと統合するヘルパーがない。

```python
# 各プロジェクトで毎回書く必要がある
async def get_request_id() -> str:
    return request_id_var.get()

@app.get("/")
async def handler(request_id: str = Depends(get_request_id)):
    ...
```

**期待する解決策**: `nene2.middleware` から `get_request_id` を直接インポートできると便利。

---

## まとめ

`RequestIdMiddleware` の基本機能（UUID v4 生成・検証・ContextVar 伝播・レスポンスヘッダー付与）は
問題なく動作する。

摩擦点:
1. **ミドルウェア順序依存のドキュメント不備** → how-to に追記
2. **`get_request_id()` Depends ヘルパーがない** → Issue 化・修正対象
