# Field Trial 48: CompositeHealthCheck + AsyncCompositeHealthCheck 実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.8 時点
**テーマ**: `CompositeHealthCheck` と `AsyncCompositeHealthCheck` を `/health` エンドポイントで使い、複数コンポーネントのヘルスチェックを集約するパターンの実運用確認

---

## 概要

同期 `CompositeHealthCheck`（DB + キャッシュ）と非同期 `AsyncCompositeHealthCheck`（DB + 外部 API）を
`/health` と `/health/async` エンドポイントで使い、部分的な失敗時の 503 レスポンスと
`checks` フィールドへの詳細情報付与を確認した。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft48-health-check/` に以下を作成:

- **`app.py`** — `CompositeHealthCheck` + `AsyncCompositeHealthCheck` を使った FastAPI アプリ
- **`test_app.py`** — 正常・503・checks フィールド・エラーメッセージ確認 (7 件)
- **`test_friction.py`** — 摩擦点の確認テスト (4 件)

**テスト結果**: 11 件全通過 ✅

---

## 摩擦点

### FP48-1: http_status_code プロパティで 200/503 が自動判定される

**分類**: 摩擦なし（良い設計の確認）

FT31 で追加した `HealthStatus.http_status_code` プロパティが
`CompositeHealthCheck` の結果でも正しく機能する。
`is_healthy` が `True` なら 200、`False` なら 503 を返す。
ハンドラーで `status_code=status.http_status_code` と書くだけで適切なステータスが返る。

---

### FP48-2: 空のチェックリストは "ok" を返す

**分類**: 摩擦なし（エッジケース確認）

`CompositeHealthCheck([])` のように空リストを渡すと、
全チェック通過として `HealthStatus(status="ok", checks={})` を返す。
ゼロ個のチェックは「失敗するチェックがない」として ok と見なす設計は直感的。

---

### FP48-3: 部分的な失敗は全コンポーネントの results を含む

**分類**: 摩擦なし（良い設計の確認）

失敗したコンポーネントのエラーメッセージと成功したコンポーネントの "ok" が
`checks` フィールドに混在する。
クライアントはどのコンポーネントが失敗したかを `checks` フィールドで判別できる。

```json
{
  "status": "error",
  "checks": {
    "database": "ok",
    "cache": "connection refused"
  }
}
```

---

### FP48-4: AsyncCompositeHealthCheck は TestClient でも並列実行される

**分類**: 摩擦なし（良い設計の確認）

`AsyncCompositeHealthCheck` は `asyncio.gather()` で並列実行するため、
TestClient（同期コンテキスト）経由でもエンドポイント内部では asyncio が使われ、
並列性が維持される。
50ms の遅延を持つチェックを含む場合でも、逐次実行の 2 倍未満の時間で完了する。

---

## フレームワーク変更

なし（全て設計通りの挙動）

---

## 関連

- `nene2.http.CompositeHealthCheck` (FT22, v1.8.0)
- `nene2.http.AsyncCompositeHealthCheck` (FT36, v1.8.4)
- `nene2.http.HealthStatus.http_status_code` (FT31, v1.8.3)
- FT22 (CompositeHealthCheck 実装, v1.8.0)
- FT31 (http_status_code プロパティ追加, v1.8.3)
- FT36 (AsyncCompositeHealthCheck 実装, v1.8.4)
