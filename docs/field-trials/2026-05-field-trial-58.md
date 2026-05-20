# FT58: ThrottleMiddleware 実運用検証

**日付**: 2026-05-20  
**テーマ**: レートリミットミドルウェア (`ThrottleMiddleware`) の実運用確認  
**バージョン**: v1.8.15  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft58-throttle/`

---

## 概要

`nene2.middleware.ThrottleMiddleware` を FastAPI に組み込み、
グローバルレート制限・エンドポイント別制限・除外パス・レートヘッダーを検証した。

---

## 実装内容

- `ThrottleMiddleware(limit=N, window=60)`: グローバルレート制限
- `path_limits={"/api/expensive": 2}`: エンドポイント別に厳しい制限
- `exclude_paths=["/health"]`: ヘルスチェックをレート制限から除外
- レスポンスヘッダー確認: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`

---

## テスト結果

**9/9 passed**

| テスト | 結果 |
|---|---|
| `test_under_limit_returns_200` | PASSED |
| `test_rate_limit_headers_present` | PASSED |
| `test_remaining_decrements_per_request` | PASSED |
| `test_exceeding_limit_returns_429` | PASSED |
| `test_429_includes_retry_after_header` | PASSED |
| `test_exclude_paths_bypass_throttle` | PASSED |
| `test_path_limits_stricter_than_global` | PASSED |
| `test_path_limits_independent_from_global` | PASSED |
| `test_429_response_is_problem_details` | PASSED |

---

## Friction Points

なし。`ThrottleMiddleware` はすべての機能が直感的に動作した。

**特筆点**:
- `path_limits` のカウンターがグローバルカウンターと独立しているのは設計どおりで便利
- `exclude_paths` でヘルスチェックを除外できるのは本番運用で必須の機能
- 429 レスポンスが RFC 9457 Problem Details 形式なのは一貫性がある
- `Retry-After` ヘッダーが自動付与される点がクライアント実装に優しい

---

## 結論

`ThrottleMiddleware` は実運用で問題なく使用できる。
`X-Forwarded-For` の信頼に関するドキュメントの警告も適切で、
リバースプロキシなし環境での注意点が明記されている。
