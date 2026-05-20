# Field Trial 39: RequestSizeLimitMiddleware 実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.4 時点
**テーマ**: `RequestSizeLimitMiddleware` で JSON ボディとバイナリアップロードのサイズを制限するパターンと、パスごとに異なる制限を設定したいユースケースの確認

---

## 概要

小さな `max_bytes` 制限（200 bytes）を設定したアプリで、正常なリクエスト・超過リクエスト・除外パス・境界値を検証した。
主な発見: パスごとに異なる制限（例: 通常 API は 1 MiB、アップロードエンドポイントは 10 MiB）が設定できない摩擦を発見。`path_limits` パラメータを追加して対応。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft39-request-size/` に以下を作成:

- **`app.py`** — `RequestSizeLimitMiddleware(max_bytes=200, exclude_paths=[...])` の動作確認アプリ
- **`test_app.py`** — 正常・超過・除外パス・境界値の動作確認 (8 件)
- **`test_friction.py`** — 摩擦点の確認テスト (3 件)

**テスト結果**: 11 件全通過 ✅

---

## 摩擦点

### FP39-1: パスごとに異なる max_bytes を設定できない

**分類**: 摩擦あり → **実装で対応**

`RequestSizeLimitMiddleware` は全体で一つの `max_bytes` のみ設定できる。
アップロードエンドポイント（例: 10 MiB）と通常 API（例: 1 MiB）で異なる制限を設定したい場合、
`exclude_paths` でアップロードを除外してハンドラー内で手動チェックするしかなかった。

**対応**: `ThrottleMiddleware.path_limits` と同様のパターンで `path_limits: dict[str, int] | None` を追加 (#259)。

```python
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_bytes=1_048_576,                  # デフォルト: 1 MiB
    path_limits={
        "/upload/file": 10_485_760,       # /upload/file: 10 MiB
        "/api/import": 5_242_880,         # /api/import: 5 MiB
    },
)
```

413 レスポンスの `max_bytes` フィールドはパス固有の制限値を返す。

---

### FP39-2: max_bytes 構造化フィールドが 413 レスポンスに含まれる（FT23 改善の確認）

**分類**: 良い設計の確認

```json
{
  "status": 413,
  "type": ".../payload-too-large",
  "title": "Payload Too Large",
  "max_bytes": 200
}
```

`max_bytes` フィールドがあることでクライアントがプログラムで制限値を知れる。
FT23 で追加された改善が実際に役立つことを確認。

---

### FP39-3: Content-Length ヘッダーによる早期拒否が機能する

**分類**: 設計通り（摩擦なし）

Content-Length ヘッダーが `max_bytes` を超える場合、ボディを読む前に 413 を返す。
メモリ効率が良い設計。

---

## フレームワーク変更

- `RequestSizeLimitMiddleware` に `path_limits: dict[str, int] | None = None` を追加 (FP39-1)
- テスト 2 件追加

---

## 関連

- `nene2.middleware.RequestSizeLimitMiddleware`
- FT12 (RequestSizeLimitMiddleware exclude_paths, v1.5.0)
- FT23 (413 レスポンスに max_bytes 追加, v1.8.0)
- FT28 (ThrottleMiddleware path_limits, v1.8.1)
- Issue #259
