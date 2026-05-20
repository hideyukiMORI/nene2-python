# FT89: カスタムバリデーション — Pydantic バリデーターと nene2 ValidationException の統合

**日付**: 2026-05-20  
**テーマ**: カスタム Pydantic バリデーター・クロスフィールド検証・nene2 ValidationException の統合  
**バージョン**: v1.8.30  
**FTディレクトリ**: `/home/xi/docker/nene2-python-FT/ft89-custom-validation/`

---

## 概要

Pydantic v2 の `@field_validator` / `@model_validator` を使ったカスタムバリデーションと
nene2 の `ValidationException` の統合を検証。
`@model_validator` で `raise ValueError(...)` すると
nene2 の Problem Details で `field: "request"` になる摩擦が発見された。

---

## 検証したパターン

### 1. クロスフィールドバリデーション（`@model_validator`）

```python
class DateRangeBody(BaseModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def end_date_after_start_date(self) -> "DateRangeBody":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self
```

✅ 動作するが、エラーレスポンスの `field` が `"request"` になる（後述）。

### 2. フィールドレベルバリデーション（`@field_validator`）

```python
class PasswordBody(BaseModel):
    @field_validator("new_password")
    @classmethod
    def new_password_not_same_as_current(cls, value: str, info: FieldValidationInfo) -> str:
        if info.data.get("current_password") == value:
            raise ValueError("new_password must differ from current_password")
        return value
```

✅ `field: "new_password"` が正しく設定される。

### 3. UseCase 層からの ValidationException

```python
def validate_business_rule(label: str) -> None:
    errors: list[ValidationError] = []
    if label.lower() in RESERVED_LABELS:
        errors.append(ValidationError(
            field="label",
            message=f"'{label}' is reserved.",
            code="reserved-label",
        ))
    if errors:
        raise ValidationException(errors)
```

✅ 完全にコントロール可能。field / message / code を自由に設定できる。

---

## 発見した問題

### 問題1: `@model_validator` のエラーが `field: "request"` になる

```python
# @model_validator で raise ValueError
# → Pydantic の loc: ("body",) or ()
# → nene2 の request_validation_error_handler で "body" を除くと空
# → field = "request" になる

# 実際のレスポンス:
{
  "type": "https://nene2.dev/problems/validation-failed",
  "errors": [
    {
      "field": "request",          # ← "end_date" や "end_date_after_start_date" ではない
      "message": "Value error, end_date must be after start_date",
      "code": "value_error"
    }
  ]
}
```

`@field_validator("end_date")` のエラーは `field: "end_date"` になるが、
`@model_validator` のエラーは `field: "request"` になる。
クライアント（TypeScript など）がフィールド単位でエラーを表示する場合、
どのフィールドにエラーが対応するかが不明になる。

### 回避策: UseCase 層で ValidationException を raise

```python
@app.post("/date-ranges")
def create_date_range(body: DateRangeBody) -> JSONResponse:
    # Pydantic の @model_validator をやめて UseCase 層で検証
    errors: list[ValidationError] = []
    if body.end_date <= body.start_date:
        errors.append(ValidationError("end_date", "end_date must be after start_date", "invalid"))
    if errors:
        raise ValidationException(errors)
    ...
```

`ValidationException` を使えば field 名を明示できる。
ただし Pydantic の `@model_validator` との二重定義になる。

---

## テスト結果（全16件パス）

```
test_date_range_valid_returns_201                             PASSED
test_date_range_end_before_start_returns_422                  PASSED
test_date_range_same_dates_returns_422                        PASSED
test_date_range_reserved_label_returns_422                    PASSED
test_password_change_valid_returns_204                        PASSED
test_password_change_same_as_current_returns_422              PASSED
test_password_change_mismatch_returns_422                     PASSED
test_password_too_short_returns_422                           PASSED
test_event_valid_returns_201                                  PASSED
test_event_empty_tag_returns_422                              PASSED
test_event_duplicate_tags_returns_422                         PASSED
test_event_too_many_tags_returns_422                          PASSED
test_explicit_error_missing_title_returns_422                 PASSED
test_validation_error_response_is_problem_details_format      PASSED
test_friction_pydantic_error_field_path_in_problem_details    PASSED
test_friction_multiple_validation_errors_all_returned         PASSED
```

---

## 摩擦ポイント一覧

| ID | 内容 | 深刻度 |
|---|---|---|
| F89-1 | `@model_validator` のエラーが `field: "request"` になり具体的なフィールド名が失われる | 中 |
| F89-2 | クロスフィールドバリデーションを Pydantic で書くか UseCase で書くかの指針がない | 低 |

---

## 使用感（主観評価）

### 直感性 ★★★★☆

Pydantic v2 の `@field_validator` は直感的で nene2 と自然に統合できる。
`@model_validator` も動くが、エラーの `field` 名が `"request"` になる不一致が惜しい。

### 実害の深刻さ ★★★☆☆

`field: "request"` 問題は、クライアントサイドがフィールド単位でバリデーション
エラーを表示しない場合（メッセージを表示するだけ）は問題にならない。
しかし TypeScript/React でフォームのフィールドにエラーを表示する場合は不便。

### 修正のしやすさ ★★★★☆

F89-1 はドキュメントだけで対応可能（`@model_validator` より `ValidationException` を推奨と明記）。
または `request_validation_error_handler` で `model_validator` の loc パターンを
検出して field 名を抽出するよう改善することも検討できる。

### 総合コメント

nene2 の `ValidationException` + `ValidationError` パターンは優れている。
フィールド名・メッセージ・コードが明示的で、クライアントに構造化エラーを返せる。
Pydantic の `@field_validator` との組み合わせも問題なし。
`@model_validator` の field パス問題は既知の FastAPI/Pydantic の挙動で、
ドキュメントで「クロスフィールドバリデーションは UseCase で行う」と案内するのが現実的。

---

## 推奨アクション

1. **docs**: how-to ガイドに「カスタムバリデーションパターン」を追加
   - `@field_validator` は nene2 Problem Details と自然に統合される
   - クロスフィールドバリデーションは `ValidationException` で行うと `field` 名が正確
   - `@model_validator` のエラーは `field: "request"` になることを明記
2. **docs**: Pydantic バリデーションと UseCase バリデーションの使い分けを説明
