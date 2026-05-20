# FT60: RequestIdMiddleware 実運用検証

**日付**: 2026-05-20  
**テーマ**: リクエストIDミドルウェア (`RequestIdMiddleware`) と `get_request_id()` の実運用確認  
**バージョン**: v1.8.15  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft60-request-id/`

---

## 概要

`nene2.middleware.RequestIdMiddleware` を FastAPI に組み込み、
UUID v4 の自動生成・クライアント指定 ID の転送・不正 ID の置き換え・
`get_request_id()` による Depends 経由でのアクセスを検証した。

---

## 実装内容

- `RequestIdMiddleware`: X-Request-Id ヘッダーの自動付与
- `get_request_id()`: `Depends` 経由でルートハンドラーからリクエストID取得
- クライアント供給 UUID v4 → そのまま転送（小文字正規化）
- クライアント供給不正値 → サーバー生成 UUID v4 に置き換え

---

## テスト結果

**7/7 passed**

| テスト | 結果 |
|---|---|
| `test_response_has_x_request_id_header` | PASSED |
| `test_generated_request_id_is_uuid_v4` | PASSED |
| `test_client_supplied_valid_uuid_v4_is_forwarded` | PASSED |
| `test_client_supplied_invalid_id_is_replaced` | PASSED |
| `test_request_id_accessible_via_depends` | PASSED |
| `test_request_id_in_depends_matches_response_header` | PASSED |
| `test_each_request_gets_unique_id` | PASSED |

---

## Friction Points

なし。`RequestIdMiddleware` と `get_request_id()` はすべて直感的に動作した。

**特筆点**:
- 不正な X-Request-Id（UUIDv4 以外）は自動で置き換えられ、ログインジェクション対策が組み込まれている
- `get_request_id()` は `Depends` で使えるため、structlog のコンテキスト設定と自然に組み合わせられる
- Depends で取得した値とレスポンスヘッダーの値が常に一致することを確認

---

## 結論

`RequestIdMiddleware` は実運用で問題なく使用できる。
セキュリティ（不正 ID の拒否）と利便性（Depends 連携）の両立が優れている。
