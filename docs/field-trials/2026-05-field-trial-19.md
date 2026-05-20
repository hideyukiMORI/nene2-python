# FT19: problem_details_response() RFC 9457 実運用検証

**日付**: 2026-05-20
**テーマ**: `problem_details_response()` を使って RFC 9457 準拠のエラー応答を実装する
**FT アプリ**: `/home/xi/docker/nene2-python-FT/ft19-problem-details/`

---

## 目的

`nene2.http.problem_details_response()` を実際のアプリ（記事 API）に組み込み、
401/404/422 のエラー応答を RFC 9457 形式で返すパターンを検証する。
また、`ErrorHandlerMiddleware` との統合状況を確認する。

---

## 実施内容

記事 CRUD API（`/articles/{article_id}`）を作成し、以下のシナリオで `problem_details_response()` を使用:

- **401 Unauthorized**: X-API-Key ヘッダー未提供または無効
- **404 Not Found**: 存在しない記事 ID へのアクセス（`extra={"article_id": article_id}` 付き）
- **422 Validation Failed**: 空のタイトルで記事作成（`extra={"errors": [...]}` 付き）

---

## テスト結果

### test_app.py（正常系・準拠確認）
| テスト | 結果 |
|---|---|
| test_get_article_success | PASS |
| test_get_article_not_found_returns_problem_details | PASS |
| test_unauthorized_returns_problem_details | PASS |
| test_validation_error_returns_problem_details | PASS |
| test_problem_details_type_is_absolute_url | PASS |

### test_friction.py（摩擦点確認）
| テスト | 結果 | 摩擦 |
|---|---|---|
| test_base_url_is_not_customizable_per_call | PASS | あり |
| test_validation_exception_and_problem_details_not_integrated | PASS | なし（当初の予想と逆） |
| test_no_typed_problem_type_constants | PASS | あり |

---

## 発見した摩擦点

### FT19-F1: プロジェクト全体の base_url を一箇所で設定できない

**概要**: `problem_details_response()` は `base_url` パラメータを持つが、
プロジェクト全体で一箇所に設定する仕組みがない。
複数のハンドラーで同じ `base_url` を保証するには、
毎回引数で渡すか、プロジェクトでラッパー関数を書く必要がある。

**影響**: 大規模プロジェクトで `base_url` の不統一が発生しやすい。

**期待する解決策**: `configure_problem_details(base_url: str)` のような
モジュールレベルの設定関数を提供する。

---

### FT19-F2: ErrorHandlerMiddleware と problem_details_response() の統合（摩擦なし）

当初「`ErrorHandlerMiddleware` が `ValidationException` を処理する際に
`application/json` を返すのではないか」と懸念していたが、
実際には `problem_details_response()` を内部で使っており、
`application/problem+json` が正しく返される。

**結論**: 摩擦なし。むしろ正しく統合されている。

---

### FT19-F3: problem_type 文字列に型安全な定数がない

**概要**: `problem_type` は文字列リテラルで渡すため、タイポがあっても
mypy では検出されない。同じプロジェクト内で `"not-found"` と `"not_found"` が
混在してもエラーにならない。

**影響**: 大規模プロジェクトで problem_type の不統一が起きやすい。

**期待する解決策**: 標準的な problem_type 定数のドキュメント化、
またはユーザーが StrEnum を使うパターンのガイダンス。
（フレームワーク側で全 problem_type を定義するのは over-engineering のため、
ドキュメントやパターン提示が適切）

---

## まとめ

`problem_details_response()` は RFC 9457 に準拠しており、`ErrorHandlerMiddleware` と
も正しく統合されている。実用上の摩擦は以下の 2 点:

1. **プロジェクト全体の base_url 設定機構がない** → Issue 化して修正対象
2. **problem_type 文字列の型安全性がない** → Issue 化してドキュメント対応

v1.4.0 で追加された `exclude_paths`、FT15-FT18 で追加された各ミドルウェア改善も
本 FT で間接的に動作確認できた。
