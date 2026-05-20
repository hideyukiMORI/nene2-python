# FT74: カスタム HealthCheckProtocol 実装の実運用検証

**日付**: 2026-05-20  
**テーマ**: ユーザー定義 `HealthCheckProtocol` / `AsyncHealthCheckProtocol` 実装と `CompositeHealthCheck` の連携  
**バージョン**: v1.8.20  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft74-custom-health/`

---

## 概要

ユーザーが `HealthCheckProtocol` を実装する実際のシナリオ（メモリ・DB・外部サービス）を
`CompositeHealthCheck` / `AsyncCompositeHealthCheck` に組み合わせて動作を検証した。

---

## 実装内容

### カスタム同期ヘルスチェック
- `AlwaysOkCheck` — 常に ok を返すベースライン
- `ToggleableCheck` — テストで on/off できるトグル可能なチェック
- `MemoryCheck` — 閾値ベースのメモリ使用量チェック（psutil なしでシミュレート）

### カスタム非同期ヘルスチェック
- `AsyncAlwaysOkCheck` — 常に ok を返す非同期版
- `AsyncToggleableCheck` — 非同期版トグルチェック

### エンドポイント
- `GET /health` — `CompositeHealthCheck` (同期)
- `GET /health/async` — `AsyncCompositeHealthCheck` (非同期)
- `create_app(db_healthy, cache_healthy, memory_usage_pct)` でテストシナリオを切り替え

---

## テスト結果

**13/13 passed**

| テスト | 結果 | 種別 |
|---|---|---|
| `test_always_ok_check_returns_ok` | PASSED | 単体 |
| `test_toggleable_check_returns_error_when_unhealthy` | PASSED | 単体 |
| `test_memory_check_ok_under_threshold` | PASSED | 単体 |
| `test_memory_check_error_over_threshold` | PASSED | 単体 |
| `test_composite_ok_when_all_checks_pass` | PASSED | 単体 |
| `test_composite_error_when_any_check_fails` | PASSED | 単体 |
| `test_health_status_http_code_200_when_ok` | PASSED | 単体 |
| `test_health_status_http_code_503_when_error` | PASSED | 単体 |
| `test_sync_health_endpoint_returns_200_when_all_ok` | PASSED | HTTP 統合 |
| `test_sync_health_endpoint_returns_503_when_db_down` | PASSED | HTTP 統合 |
| `test_sync_health_endpoint_returns_503_when_memory_high` | PASSED | HTTP 統合 |
| `test_async_health_endpoint_returns_200_when_all_ok` | PASSED | HTTP 統合 |
| `test_async_health_endpoint_returns_503_when_cache_down` | PASSED | HTTP 統合 |

---

## Friction Points

なし。

**特筆点**:
- `HealthCheckProtocol` / `AsyncHealthCheckProtocol` はどちらも `@runtime_checkable Protocol` なので、
  特定の基底クラスを継承せずとも `check()` メソッドを実装するだけで準拠できる。
- `CompositeHealthCheck` は各チェックの `checks` dict をフラットマージするため、
  複数チェックが同一キーを持つと後のチェックが上書きする。キーの命名が重要。
- `HealthStatus.http_status_code` は 200 / 503 を自動で返すため、
  HTTP ハンドラーで `status_code=status.http_status_code` とするだけで正しいステータスコードになる。
- `create_app(db_healthy=False)` の DI パターンで HTTP テストにおける「障害シミュレーション」が簡潔に書ける。

---

## 結論

`HealthCheckProtocol` の実装は `check() -> HealthStatus` を持つだけで完了する。
`CompositeHealthCheck` がフラットマージすることを把握した上で、
各チェックのキー命名を一意にすれば、複数チェックの組み合わせは完全に直感的に動作する。
