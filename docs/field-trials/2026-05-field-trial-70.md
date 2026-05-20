# FT70: 複数ドメイン連携 実運用検証

**日付**: 2026-05-20  
**テーマ**: 複数ドメイン連携（Post + Comment ネストリソース API）の実運用確認  
**バージョン**: v1.8.19  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft70-multi-domain/`

---

## 概要

Post ドメインと Comment ドメインを組み合わせたネストリソース API を実装し、
複数のフレームワーク機能を同時に使用した際の統合動作を検証した。

---

## 実装内容

- `GET /posts` — `PaginationQueryParser` + `PaginationResponse` でページネーション
- `POST /posts` — `SqlAlchemyTransactionManager.transactional()` でインサート
- `GET /posts/{post_id}` — 存在しない場合 404 (Problem Details)
- `GET /posts/{post_id}/comments` — 親リソース存在チェック付きページネーション
- `POST /posts/{post_id}/comments` — 親リソース存在チェック付きインサート
- `RequestIdMiddleware` + `ErrorHandlerMiddleware` をスタック
- `StaticPool` を使ったインメモリ SQLite（接続共有）
- `dataclass(frozen=True, slots=True)` を Post / Comment の値オブジェクトに使用

---

## テスト結果

**10/10 passed**

| テスト | 結果 |
|---|---|
| `test_list_posts_returns_paginated` | PASSED |
| `test_get_post_returns_200` | PASSED |
| `test_get_nonexistent_post_returns_404` | PASSED |
| `test_create_post_returns_201` | PASSED |
| `test_list_comments_for_post` | PASSED |
| `test_list_comments_for_nonexistent_post_returns_404` | PASSED |
| `test_create_comment_returns_201` | PASSED |
| `test_create_comment_for_nonexistent_post_returns_404` | PASSED |
| `test_request_id_header_present` | PASSED |
| `test_comment_count_increases_after_create` | PASSED |

---

## Friction Points

なし。複数ドメインを組み合わせた際もすべてのフレームワーク機能が正常に動作した。

**特筆点**:
- `StaticPool` は FT67 で習得済みのため、インメモリ SQLite の設定は迷わず実施できた
- `PaginationQueryParser` + `PaginationResponse` のネストリソース（`/posts/{id}/comments`）への適用も自然
- `SqlAlchemyTransactionManager.transactional()` で Post と Comment の両インサートが問題なく動作
- `RequestIdMiddleware` は `ErrorHandlerMiddleware` と共存可能（ミドルウェアスタック順序の制約なし）
- `problem_details_response()` の 404 応答は親リソース (`post-not-found`) に統一可能

---

## 結論

nene2-python の主要機能（Pagination, Transaction, RequestId, ErrorHandler, Problem Details）を
複数ドメイン連携シナリオで組み合わせても一切の摩擦がなかった。
FT57〜FT69 で修正・ドキュメント化された機能がすべて期待通り動作し、
フレームワークの統合品質が高いことを確認できた。
