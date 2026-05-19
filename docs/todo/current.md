# TODO — current

最終更新: 2026-05-20
現状: **v1.x 完了済み / 敵対的評価に基づく改善 PR レビュー中**

---

## 状態サマリー

v0.1.0〜v1.x のすべてのマイルストーンが完了しています。
2026-05-20 の敵対的評価に基づき、13 件の改善 PR を作成・対応済みです。

---

## オープン PR（マージ待ち）

### コード品質改善（第一弾）

| PR | Issue | 優先度 | 内容 |
|---|---|---|---|
| [#114](https://github.com/hideyukiMORI/nene2-python/pull/114) | #107 | 高 | `McpHttpResponse.body` 型誤記修正（docs） |
| [#115](https://github.com/hideyukiMORI/nene2-python/pull/115) | #108 | 中 | `PaginationQueryParser` 非整数パラメータで 500→ValidationException |
| [#116](https://github.com/hideyukiMORI/nene2-python/pull/116) | #112 | 中低 | `SecurityHeadersMiddleware` CSP が `/docs` を壊す問題を修正 |
| [#117](https://github.com/hideyukiMORI/nene2-python/pull/117) | #110 | 低 | note/tag Input dataclass に `slots=True` 追加 |
| [#118](https://github.com/hideyukiMORI/nene2-python/pull/118) | #109 | 低 | Get UseCase を typed Input DTO パターンに統一 |
| [#119](https://github.com/hideyukiMORI/nene2-python/pull/119) | #111/#113 | 低 | ThrottleMiddleware X-Forwarded-For リスク明記 + テスト fixture 整理 |

### 敵対的評価に基づく修正（第二弾）

| PR | Issue | 優先度 | 内容 |
|---|---|---|---|
| [#133](https://github.com/hideyukiMORI/nene2-python/pull/133) | #120 | 高 | `RequestSizeLimitMiddleware` Content-Length 省略で制限回避できる問題を修正 |
| [#134](https://github.com/hideyukiMORI/nene2-python/pull/134) | #121 | 高 | `ApiKeyAuthMiddleware` が `TokenVerificationException` を捕捉せず 500 漏洩 |
| [#135](https://github.com/hideyukiMORI/nene2-python/pull/135) | #122 | 高 | `X-Request-Id` 未検証によるログインジェクション修正 |
| [#136](https://github.com/hideyukiMORI/nene2-python/pull/136) | #123 | 中 | コメント handler の `note_id` 無視バグ修正・REST 階層整合性 |
| [#137](https://github.com/hideyukiMORI/nene2-python/pull/137) | #124 | 中 | `comments.note_id` 外部キー制約 + ON DELETE CASCADE 追加 |
| [#138](https://github.com/hideyukiMORI/nene2-python/pull/138) | #125/#126/#127 | 中 | HealthCheck/BoundExecutor/CORS ヘッダーの中優先度バグ修正 |
| [#139](https://github.com/hideyukiMORI/nene2-python/pull/139) | #128〜#132 | 低 | InMemory sort / type: ignore reason / app_env 検証 / CI matrix / docs |

---

## 検討中の次のステップ

- **Field Trial 7**: 親子リソース / MySQL・PostgreSQL / PyPI 公開フロー（検討中）
- **WebSocket サポート**: 検討中
- **PyPI 公開**: パッケージメタデータ整備済み（v1.x 完了後に実施予定）

---

## 直近のフィールドトライアル

| FT | テーマ | 結果 |
|---|---|---|
| FT1 | InMemory CRUD + git+ インストール | 完了 ✅ |
| FT2 | SQLite 永続化 | 完了 ✅ |
| FT3 | Bearer Token 認証 + MCP stdio | 完了 ✅ |
| FT4 | MCP + SQLite 共有 / ApiKey / CORS | 完了 ✅ |
| FT5 | transactional() DX（ウォレット送金 API）| 完了 ✅ |
| FT6 | AsyncUseCaseProtocol DX（天気ダッシュボード）| 完了 ✅ |
