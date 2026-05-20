# Field Trial 13 — ValidationException 実運用

**Date:** 2026-05-20
**App:** User Registration API（メール・パスワード・年齢の複合バリデーション）
**Directory:** `/home/xi/docker/nene2-python-FT/ft13-validation/`
**nene2-python version:** v1.5.0

## 概要

`ValidationException` と `ValidationError` を実際のアプリで使い、
複数フィールドのバリデーション・複数エラーの集約・レスポンス形式を検証した。

## 動作確認結果

- 複数フィールドのバリデーションエラーが一度に返ること ✓（fail-fast ではなく fail-all）
- `ErrorHandlerMiddleware` が `ValidationException` を 422 に変換すること ✓
- レスポンスが RFC 9457 形式で `errors` 配列を含むこと ✓
- `ValidationError` の `field`, `message`, `code` が全フィールドで返ること ✓

## 摩擦点

### FT13-F1 (LOW): 単一エラーでもリストラップが必要

単一フィールドのエラーでも `list` でラップする必要があり、やや冗長。

```python
# 現状（毎回リストが必要）
raise ValidationException([ValidationError("email", "invalid", "invalid_email")])

# こうしたい
raise ValidationException.single("email", "invalid", "invalid_email")
```

特に UseCase 層で早期リターンするケース（1つのエラーが致命的で後続チェック不要な場合）に
`ValidationException([...])` は読みにくい。

### FT13-F2 (LOW): ValidationError の空文字エラーメッセージがどのフィールドか不明

`ValidationError("", "message", "code")` を作ると `ValueError: field, message, and code must be non-empty strings` が出るが、どのフィールドが空かわからない。開発時のデバッグに時間がかかる。

```python
# 現状
ValidationError("", "msg", "code")
# → ValueError: field, message, and code must be non-empty strings

# 改善案
# → ValueError: ValidationError.field must not be empty
```

## まとめ

`ValidationException` の基本動作は問題なし。摩擦は軽微で、実務で使うのに大きな障壁はない。
FT13-F1 の `ValidationException.single()` はよくある単一エラーケースの DX 改善として有用。
FT13-F2 はデバッグ時の QoL 向上。どちらも LOW 優先度。
