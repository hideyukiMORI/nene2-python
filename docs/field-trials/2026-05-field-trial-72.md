# FT72: DatabaseIntegrityException + write() 戻り値パターン実運用検証

**日付**: 2026-05-20  
**テーマ**: ユニーク制約違反 (409) と UPDATE/DELETE の rowcount=0 (404) パターン検証  
**バージョン**: v1.8.19  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft72-db-integrity/`

---

## 概要

ユーザー登録 API でユニーク制約違反 → `DatabaseIntegrityException` → 409 のマッピングと、
`write()` 戻り値 0 を使った UPDATE/DELETE の「対象なし → 404」パターンを実運用で検証した。
あわせて `request_validation_error_handler` による Pydantic 422 → nene2 形式変換も確認した。

---

## 実装内容

- `users` テーブル（`username UNIQUE`, `email UNIQUE`）
- `POST /users` — INSERT、重複時 `DatabaseIntegrityException` → 409
- `GET /users/{id}` — 存在しない場合 404
- `PUT /users/{id}/email` — UPDATE、`write()` 戻り値 0 → 404
- `DELETE /users/{id}` — DELETE、`write()` 戻り値 0 → 404、成功時 204
- `SimpleDomainHandler(DatabaseIntegrityException, "user-conflict", "Conflict", 409)` で自動変換
- `app.add_exception_handler(RequestValidationError, request_validation_error_handler)` で Pydantic 422 形式統一

---

## テスト結果

**11/11 passed**

| テスト | 結果 |
|---|---|
| `test_register_user_returns_201` | PASSED |
| `test_register_duplicate_username_returns_409` | PASSED |
| `test_register_duplicate_email_returns_409` | PASSED |
| `test_get_user_returns_200` | PASSED |
| `test_get_nonexistent_user_returns_404` | PASSED |
| `test_update_email_returns_200` | PASSED |
| `test_update_email_for_nonexistent_user_returns_404` | PASSED |
| `test_update_to_duplicate_email_returns_409` | PASSED |
| `test_delete_user_returns_204` | PASSED |
| `test_delete_nonexistent_user_returns_404` | PASSED |
| `test_register_invalid_body_returns_422_nene2_format` | PASSED |

---

## Friction Points

なし。

**特筆点**:
- `SimpleDomainHandler(DatabaseIntegrityException, ...)` で SQLAlchemy の IntegrityError を
  透過的に 409 に変換できる。ハンドラー側のコードに `try/except` が不要。
- `write()` の戻り値セマンティクス（UPDATE/DELETE は rowcount、INSERT は lastrowid）により、
  `if affected == 0: return 404` パターンが自然に書ける。
- `JSONResponse(None, status_code=204)` が 204 No Content として正しく動作する。
- `request_validation_error_handler` を `add_exception_handler(RequestValidationError, ...)` で
  登録することで、Pydantic の 422 バリデーションエラーも nene2 の `validation-failed`
  Problem Details 形式に統一できる。`ErrorHandlerMiddleware` だけではこのケースをカバーできないため、
  完全な 422 形式統一には両方の登録が必要。

---

## 結論

`DatabaseIntegrityException` は `SimpleDomainHandler` で宣言的に 409 にマッピングでき、
`write()` の 0 戻り値で UPDATE/DELETE の「対象なし → 404」も慣用的に書ける。
Pydantic バリデーション 422 の形式統一には `request_validation_error_handler` の追加登録が必要な点は
覚えておく価値がある。
