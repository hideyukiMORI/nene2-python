# FT277: keyword — iskeyword / issoftkeyword / 識別子検証

**日付**: 2026-05-29
**テーマ**: Python `keyword` モジュールの予約語判定・識別子検証の実装と検証
**セキュリティ診断**: なし（277 % 3 = 1）
**クラッカーペンテスト**: なし（277 % 4 = 1）

---

## 概要

`keyword` は Python 予約語の判定を提供する。ユーザー指定の識別子（フィールド名・変数名・属性名）を受け付ける際、**予約語でないこと**の検証に使う。HTTP API でラップし `iskeyword`/`issoftkeyword` + `str.isidentifier` の組み合わせを検証した。

| API | ユースケース |
|---|---|
| `keyword.iskeyword(s)` | 予約語（if/for/class 等）判定 |
| `keyword.issoftkeyword(s)` | ソフトキーワード（match/case/type/_）判定 |
| `str.isidentifier()` | 識別子として妥当か |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft277-keyword/`

| 関数 | 概要 |
|---|---|
| `check_name()` | is_identifier / is_keyword / is_soft_keyword / is_safe_identifier |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/keyword/check` | 識別子・予約語の判定 |

---

## 摩擦点

### F-1: `str.isidentifier` は予約語も True にする

**観察**: `"class".isidentifier()` は `True`。`isidentifier` は構文上の識別子かを見るだけで、予約語かは判定しない。これだけで「使える名前」と判断すると、コード生成や `setattr` で予約語名を使い構文エラーになる。

**対処**: `is_safe_identifier = isidentifier() and not iskeyword()`。`class` は識別子だが予約語なので安全でないと判定。

### F-2: ソフトキーワード（match/case/type/_）は通常の識別子として使える

**観察**: `match`/`case`/`type`/`_` は**ソフトキーワード**で、文脈によってはキーワードだが**変数名としても使える**（`iskeyword("match")` は False）。`issoftkeyword` で別途判定できる。

**対処**: `is_soft_keyword` を返しつつ、`is_safe_identifier` は True（変数名として使えるため）。用途次第でソフトキーワードを避ける判断もできる。

### F-3: 識別子でない入力

**観察**: `123abc`・空文字・スペース入りは識別子でない。

**対処**: `isidentifier()` で判定、空は 422。

---

## テスト結果

```
5 passed in 1.03s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`class` が変数名に使えない理由を学べる。識別子と予約語の違いが分かる。

**ドキュメント理解**: isidentifier が予約語も True にする点をコメントで明示。
**事故リスク（低）**: 判定のみ。
**規約の使いやすさ**: name → 各種フラグが分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

動的なフィールド名・属性名生成で使う。予約語チェック漏れで構文エラーを作りやすい。

**コピペ可能性**: check_name は流用可。
**拡張時の罠**: isidentifier だけで判定・ソフトキーワード。
**事故リスク（低）**: 組み合わせ判定。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS の予約語チェックに対応。識別子ルールは言語ごとに異なる。

**エラーレスポンスの質**: 空は 422。
**Python 固有概念**: ソフトキーワード。
**事故リスク（低）**: 判定あり。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

ORM のフィールド名・dataclass のフィールド生成で使う。予約語回避は dataclasses も内部で考慮。

**他フレームワークとの差異**: 大差なし。
**nene2 の薄さへの評価**: 組み合わせ判定が実用的。
**事故リスク（低）**: 判定のみ。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- ユーザー指定識別子を `isidentifier() and not iskeyword()` で検証しているか。
- ソフトキーワードの扱いを用途に応じ判断しているか。
- 動的属性アクセス（setattr/getattr）の前に名前検証しているか。
- 長さ上限。

**チームでの安全なパターン**: 動的名は is_safe_identifier で検証してから使用。
**事故リスク（低）**: 組み合わせ判定を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。
**初心者でも安全な API 達成度**: isidentifier + iskeyword の組み合わせを関数内に固定。
**改善提案**: 動的属性アクセス（getattr）の前に is_safe_identifier 検証を必須化する how-to を用意する。
