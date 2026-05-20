# FT31: DatabaseHealthCheck + ヘルスエンドポイント統合検証

**日付**: 2026-05-20
**テーマ**: `DatabaseHealthCheck` と `/health` エンドポイントの統合パターン検証
**FT アプリ**: `/home/xi/docker/nene2-python-FT/ft31-health-check/`

---

## 目的

`DatabaseHealthCheck` + `CompositeHealthCheck` を使った `/health` エンドポイントの実装パターンを検証する。

---

## 実施内容

- `DatabaseHealthCheck` + `CompositeHealthCheck` で `/health` を実装
- DB 接続成功時に 200、失敗時に 503 を返すパターンを確認
- フレームワークが提供すべき機能の不足を記録

---

## テスト結果

### test_app.py（正常系・機能確認）
| テスト | 結果 |
|---|---|
| test_health_endpoint_returns_200_when_db_healthy | PASS |
| test_health_includes_all_checks | PASS |
| test_ping_returns_200 | PASS |
| test_health_returns_503_when_db_fails | PASS |

### test_friction.py（摩擦点確認）
| テスト | 結果 | 摩擦 |
|---|---|---|
| test_health_endpoint_has_no_built_in_route | PASS | 軽微（how-to 推奨パターン記載で対応） |
| test_health_status_lacks_http_status_code_mapping | PASS | あり |

---

## 発見した摩擦点

### FT31-F1: HealthStatus が HTTP ステータスコードのマッピングを持たない

**概要**: `/health` エンドポイントを実装するとき、
`status="ok"` → 200、`status="error"` → 503 のマッピングを毎回手動で書く必要がある。

```python
# 毎回このボイラープレートが必要
http_status = 200 if status.is_healthy else 503
return JSONResponse({"status": status.status}, status_code=http_status)

# 期待する使い方
return JSONResponse({"status": status.status}, status_code=status.http_status_code)
```

**期待する解決策**: `HealthStatus` に `http_status_code: int` プロパティを追加する。

---

## まとめ

`DatabaseHealthCheck` + `CompositeHealthCheck` の基本機能は問題なく動作する。

摩擦点:
1. **`HealthStatus.http_status_code` プロパティがない** → Issue 化・修正対象
