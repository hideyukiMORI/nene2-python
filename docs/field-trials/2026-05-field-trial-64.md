# FT64: ValidationException 複数エラー実運用検証

**日付**: 2026-05-20  
**テーマ**: 複数フィールドの `ValidationException` 集積と `ValidationError` 実運用確認  
**バージョン**: v1.8.16 → v1.8.17 (修正含む)  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft64-multi-validation/`

---

## 概要

`ValidationException` を使って複数フィールドのバリデーションエラーを集積し、
一度に 422 レスポンスとして返す実運用パターンを検証した。

---

## 実装内容

- `RegisterUserBody`: username・email・age の 3 フィールドを Pydantic で受け取る
- `_validate_registration()`: エラーを `list[ValidationError]` に集積して `ValidationException(errors)` を raise
- 複数エラーが一度に返されること、Problem Details 形式であることを確認

---

## テスト結果

**7/7 passed** (v1.8.17 で修正後)

| テスト | 結果 |
|---|---|
| `test_valid_registration_returns_201` | PASSED |
| `test_single_invalid_email_returns_422` | PASSED |
| `test_underage_user_returns_422` | PASSED |
| `test_multiple_errors_returned_at_once` | PASSED |
| `test_422_response_is_problem_details_format` | PASSED |
| `test_errors_include_field_message_code` | PASSED |
| `test_pydantic_validation_error_returns_422` | PASSED |

---

## Friction Points

### FP-1: `ValidationError(field, message, code)` の引数順で `message` と `code` を混同

**発生箇所**: `app.py` で `ValidationError` を直接構築した際

**症状**:
```python
# 意図: code="invalid_email"
ValidationError("email", "invalid_email", "メールアドレスの形式が正しくありません")
# → message="invalid_email", code="メールアドレスの形式が正しくありません" になってしまう
```

**原因**: `(field, message, code)` の順序で、短い機械可読コードを先に書きたくなるが
`message` が先に来るため混同が起きやすい。

**修正**: 
- `ValidationError.code` にスペースを含む場合 `ValueError` を早期発生させる (v1.8.17)
- docstring にキーワード引数付き例を追加してどちらが何かを明確化

---

## 結論

`ValidationException` の複数エラー集積パターンは実運用で問題なく使用できる。
`message` と `code` の混同を防ぐ `ValueError` と docstring 改善により、
今後は早期にミスに気づけるようになった。
