# Field Trial 36: CompositeHealthCheck 実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.3 時点
**テーマ**: `CompositeHealthCheck` で複数の依存サービス（DB・外部 API・キャッシュ）の健全性を集約し、`HealthStatus.http_status_code` を使って `/health` エンドポイントを実装するパターン。および非同期ヘルスチェックのギャップを発見・修正。

---

## 概要

SQLite DB・外部 API（モック）・キャッシュ（モック）の 3 つの依存を `CompositeHealthCheck` で集約し、
部分障害時に個別のチェック名と全体 `"error"` ステータスを返すパターンを検証した。

主な発見: 非同期チェックに対応するプロトコルとクラスがなく、外部 HTTP API を非同期で確認するヘルスチェックが書けない摩擦を発見。`AsyncHealthCheckProtocol` と `AsyncCompositeHealthCheck` を追加して対応。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft36-composite-health/` に以下を作成:

- **`app.py`** — DB / 外部 API / キャッシュの 3 チェックを集約した `/health` エンドポイント
- **`test_app.py`** — 全正常・DB 障害・部分障害・各チェック名の確認 (5 件)
- **`test_friction.py`** — 摩擦点の確認テスト (4 件)

**テスト結果**: 9 件全通過 ✅

---

## 摩擦点

### FP36-1: 非同期ヘルスチェックに対応するプロトコルがない

**分類**: 摩擦あり → **実装で対応**

`HealthCheckProtocol.check()` は同期のみ。外部 HTTP API への非同期 `httpx.AsyncClient` 呼び出しや
非同期 DB クライアントを使うヘルスチェックを書けない。

**対応**: `AsyncHealthCheckProtocol` と `AsyncCompositeHealthCheck` を `nene2.http` に追加 (#254)。
`asyncio.gather` で全チェックを並列実行するため、レスポンスタイムも最適化される。

```python
class AsyncApiHealthCheck:
    async def check(self) -> HealthStatus:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://api.example.com/health")
        status = "ok" if r.status_code == 200 else "error"
        return HealthStatus(status=status, checks={"external_api": status})

composite = AsyncCompositeHealthCheck([db_check, AsyncApiHealthCheck()])
```

---

### FP36-2: チェックの名前を集約時に指定できない

**分類**: 設計通り（摩擦なし）

チェックの名前は `HealthStatus.checks` の dict キーで決まる（チェック実装側が定義する）。
集約側での名前 override はできない。

**判断**: チェック実装がその名前を知っているべきという責務分離の観点で正しい設計。
集約側での名前指定を可能にすると DRY 違反になりやすい。

---

### FP36-3: 同名キーを持つチェックが複数あると後勝ちになる

**分類**: 軽微な摩擦（ドキュメント対応）

2 つのチェックが同じキーを `checks` に返した場合、`dict.update()` で後のチェックが勝つ。
衝突検出の仕組みはない。

**判断**: 各チェックがユニークな名前を使う規約で対応。

---

## フレームワーク変更

- `nene2.http.AsyncHealthCheckProtocol` — `async def check() -> HealthStatus` の Protocol を追加 (FP36-1)
- `nene2.http.AsyncCompositeHealthCheck` — 並列実行の集約クラスを追加 (FP36-1)
- テスト 6 件追加

---

## 関連

- `nene2.http.CompositeHealthCheck`
- `nene2.http.HealthStatus`
- FT22 (CompositeHealthCheck 実装, v1.8.0)
- FT31 (HealthStatus.http_status_code, v1.8.3)
- Issue #254
