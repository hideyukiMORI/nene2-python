# FT22: HealthCheckProtocol 実運用検証

**日付**: 2026-05-20
**テーマ**: `HealthCheckProtocol` を使ったヘルスチェックエンドポイントの実運用検証
**FT アプリ**: `/home/xi/docker/nene2-python-FT/ft22-health-check/`

---

## 目的

`nene2.http.HealthCheckProtocol` と `DatabaseHealthCheck` を使って
DB + 外部サービスを組み合わせた `/health` エンドポイントを実装するパターンを検証する。

---

## 実施内容

- SQLite in-memory DB の `DatabaseHealthCheck` を組み込み
- 外部 API の可用性を表す `ExternalApiHealthCheck`（モック）を実装
- 両者を組み合わせる `CompositeCheck`（手動実装）を作成
- `/health` エンドポイントを手動で FastAPI に登録

---

## テスト結果

### test_app.py（正常系・機能確認）
| テスト | 結果 |
|---|---|
| test_health_returns_200_when_all_checks_pass | PASS |
| test_health_returns_503_when_service_unavailable | PASS |
| test_database_check_passes | PASS |
| test_api_data_endpoint_works | PASS |

### test_friction.py（摩擦点確認）
| テスト | 結果 | 摩擦 |
|---|---|---|
| test_no_composite_health_check_provided | PASS | あり |
| test_health_endpoint_not_integrated_with_framework | PASS | あり |
| test_health_status_checks_is_flat_string_dict | PASS | あり（軽微） |

---

## 発見した摩擦点

### FT22-F1: 複数チェックを集約する CompositeHealthCheck がない

**概要**: DB チェック + 外部サービスチェックなど複数の `HealthCheckProtocol` を
組み合わせる場合、毎回集約クラスを手書きする必要がある。

**影響**: 実運用では複数チェックの組み合わせが一般的で、
その度に同じ集約ロジックを再実装することになる。

**期待する解決策**: `CompositeHealthCheck(checks: list[HealthCheckProtocol])` クラスを
`nene2.http` に追加する。

---

### FT22-F2: /health エンドポイントの FastAPI 登録ヘルパーがない

**概要**: `HealthCheckProtocol` を実装しても、それを `/health` エンドポイントとして
FastAPI に登録する仕組みがない。毎回同じパターンのエンドポイント定義を手書きする必要がある。

**影響**: ボイラープレートが多い（status_code 分岐、JSON レスポンス形式など）。

**期待する解決策**: `CompositeHealthCheck` 自体に FastAPI ルーターを生成するメソッドを
追加するより、`CompositeHealthCheck` があれば残りは app.py 側で 5 行で済むため、
今回は F1 の修正で十分と判断。

---

### FT22-F3: HealthStatus.checks が dict[str, str] のみ（軽微）

**概要**: `HealthStatus.checks` の型が `dict[str, str]` のため、
レイテンシや接続プール情報などの構造化詳細を含めることができない。

**判断**: RFC ヘルスチェックの標準的な形式は文字列ステータスで十分なため、
現状の型で問題なし。要件があれば `extra` フィールドを追加する方向で対応。

---

## まとめ

`HealthCheckProtocol` と `DatabaseHealthCheck` は機能するが、
複数チェックの集約クラスがないため実運用で毎回同じコードを書く必要がある。

`CompositeHealthCheck` の追加が最も有効な改善（FT22-F1 → Issue化・修正対象）。
