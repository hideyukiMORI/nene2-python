# Field Trial 105: マルチテナント DB 接続

## テーマ

`X-Tenant-Id` ヘッダーでテナントを切り替え、リクエストごとに異なる SQLite DB に接続するマルチテナントパターンを検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft105-multitenant/` に以下を実装:

- `TENANT_DB_URLS` マップでテナント DB URL を管理
- `get_tenant_session()` Depends でテナント特定・セッション生成
- テナント分離テスト（A と B は独立した DB）

## テスト結果

全 6 テスト通過。

## Friction Points

### FP1: `create_engine()` をリクエストごとに呼ぶのはパフォーマンス上の問題

**状況**: `get_tenant_session()` がリクエストごとに `create_engine()` を呼ぶ。SQLAlchemy では `create_engine()` はアプリ起動時に一度だけ呼ぶべきで、コネクションプールを使い回す設計が推奨される。

nene2 にテナントごとのエンジンキャッシュパターンがない。`TtlCache[Session]` で代替できるが、セッションはリクエストスコープで閉じる必要があるため、エンジンをキャッシュすべき。

```python
# 推奨パターン
_engine_cache: dict[str, Engine] = {}

def get_engine(tenant_id: str) -> Engine:
    if tenant_id not in _engine_cache:
        _engine_cache[tenant_id] = create_engine(TENANT_DB_URLS[tenant_id], ...)
    return _engine_cache[tenant_id]
```

### FP2: `SqlAlchemyQueryExecutor` はシングルエンジン想定

**状況**: `nene2.database.SqlAlchemyQueryExecutor` はアプリ起動時に単一エンジンで初期化することを前提としている。マルチテナントでリクエストごとに異なるエンジンを使う場合、`SqlAlchemyQueryExecutor` を使わず直接 `Session` を操作する必要がある。

## まとめ

FP1 は `TtlCache` を使ったエンジンキャッシュパターンとして docs に追記する。FP2 はアーキテクチャ設計上の制約として記録。コード修正は不要。
