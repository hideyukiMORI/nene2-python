# TODO — current

最終更新: 2026-05-20
現状: **v1.x 完了済み / コード品質改善 PR レビュー中**

---

## 状態サマリー

v0.1.0〜v1.x のすべてのマイルストーンが完了しています。
2026-05-20 のコード品質評価に基づき、以下の改善 PR を作成中です。

---

## オープン PR（マージ待ち）

| PR | Issue | 優先度 | 内容 |
|---|---|---|---|
| [#114](https://github.com/hideyukiMORI/nene2-python/pull/114) | #107 | 高 | `McpHttpResponse.body` 型誤記修正（docs） |
| [#115](https://github.com/hideyukiMORI/nene2-python/pull/115) | #108 | 中 | `PaginationQueryParser` 非整数パラメータで 500→ValidationException |
| [#116](https://github.com/hideyukiMORI/nene2-python/pull/116) | #112 | 中低 | `SecurityHeadersMiddleware` CSP が `/docs` を壊す問題を修正 |
| [#117](https://github.com/hideyukiMORI/nene2-python/pull/117) | #110 | 低 | note/tag Input dataclass に `slots=True` 追加 |
| [#118](https://github.com/hideyukiMORI/nene2-python/pull/118) | #109 | 低 | Get UseCase を typed Input DTO パターンに統一 |
| [#119](https://github.com/hideyukiMORI/nene2-python/pull/119) | #111/#113 | 低 | ThrottleMiddleware X-Forwarded-For リスク明記 + テスト fixture 整理 |

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
