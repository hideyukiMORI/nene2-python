# Field Trial 54: RequestSizeLimitMiddleware + path_limits 実運用検証

**Date**: 2026-05-20
**Theme**: `RequestSizeLimitMiddleware` + `path_limits` の実運用パターン検証
**Version under test**: v1.8.13
**FT App**: `/home/xi/docker/nene2-python-FT/ft54-size-limit/`

---

## 概要

ファイルアップロード API で `RequestSizeLimitMiddleware` の `path_limits` を使い、
エンドポイントごとに異なるサイズ上限を設定した。

---

## 実装内容

```python
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_bytes=10 * KB,          # デフォルト: 10KB
    path_limits={
        "/upload/avatar":   50 * KB,   # プロフィール画像
        "/upload/document": 200 * KB,  # ドキュメント
    },
    exclude_paths=["/health"],
)
```

`path_limits` の値はデフォルト `max_bytes` を上書きする。
`/upload/avatar` は `10KB` 超過でも `50KB` 以下なら受け入れる。

---

## テスト結果

9 tests, all passed.

| テスト | 結果 |
|---|---|
| /health は除外 | ✅ |
| /data の 5KB はデフォルト内 | ✅ |
| /data の 11KB がデフォルト超過 → 413 | ✅ |
| 413 が Problem Details 形式 (max_bytes フィールド含む) | ✅ |
| /upload/avatar の 40KB は path_limits 内 | ✅ |
| /upload/avatar の 51KB が path_limits 超過 → 413 | ✅ |
| /upload/document の 150KB は path_limits 内 | ✅ |
| /upload/document の 201KB が path_limits 超過 → 413 | ✅ |
| path_limits がデフォルトを上書きすることを確認 | ✅ |

---

## 摩擦ポイント

摩擦なし。`path_limits` の設定は直感的で期待通りに動作した。

413 レスポンスに `max_bytes` フィールドが含まれるため、クライアントが上限値を把握できる。

---

## フレームワーク変更

なし。

---

## 結論

`RequestSizeLimitMiddleware` の `path_limits` はファイルアップロード API の実運用で
摩擦なく使える。デフォルト + パスごとのオーバーライドという設計が直感的。
