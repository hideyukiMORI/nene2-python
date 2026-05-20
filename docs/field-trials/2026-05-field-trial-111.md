# Field Trial 111: カーソルベースページネーション

## テーマ

ID ベースのカーソル（Base64 エンコード）で大規模データを安定的にページングするパターンを検証する。
既存の `PaginationQueryParser`（オフセット型）との比較として実装する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft111-cursor-pagination/` に以下を実装:

- `after` クエリパラメータ + `limit` でカーソルページネーション
- `next_cursor` / `has_next` を含む `CursorPage` レスポンスモデル
- Base64 URL-safe エンコードでカーソルを不透明にする
- 100件のサンプルデータで重複なし検証
- 7 テスト通過（修正後）

## テスト結果

全 7 テスト通過（1件修正後）。

## Friction Points

### FP1: 無効なカーソルで `binascii.Error` が捕捉されず 500 になる

**状況**: `?after=invalidcursor!` のような無効な Base64 文字列を渡すと、
`base64.urlsafe_b64decode()` が `binascii.Error` を raise する。
これを捕捉しないと `ErrorHandlerMiddleware` が 500 として返す。

```python
# ❌ binascii.Error が uncaught → 500
after_id = _decode_cursor(after)

# ✅ try-except でカーソルデコードを保護する
try:
    after_id = _decode_cursor(after)
except Exception:
    return JSONResponse({"detail": "Invalid cursor"}, status_code=400)
```

**影響**: 中。入力バリデーションとして当然捕捉すべきだが、
Pydantic の `Query()` では Base64 形式の検証はできない（文字列型のみ）。
カーソルデコードは必ず try-except で保護する必要がある。

**代替案**: `ValidationException` を raise して 422 にするパターンもあるが、
不正なカーソルは「バリデーションエラー」ではなく「不正リクエスト」なので 400 が適切。

## まとめ

FP1 を how-to に追記。カーソルのデコードは必ず try-except で保護し 400 を返す。
オフセットページネーションとの使い分け:
- オフセット型: 件数が少ない、管理画面など「ページ番号」で飛びたい場合
- カーソル型: 件数が多い、リアルタイムデータ、無限スクロールなど
