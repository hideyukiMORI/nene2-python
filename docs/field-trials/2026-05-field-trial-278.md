# FT278: string — capwords / 定数（文字種判定）

**日付**: 2026-05-29
**テーマ**: Python `string` モジュールの定数・capwords の実装と検証
**セキュリティ診断**: なし（278 % 3 = 2）
**クラッカーペンテスト**: なし（278 % 4 = 1）

---

## 概要

`string` モジュールは文字集合の定数（`ascii_letters`/`digits`/`punctuation`/`printable`）と `capwords` を提供する。HTTP API でラップし単語の大文字化と ASCII 文字種判定を検証した。FT236（Template）/FT248（Formatter）は string のサブ機能で、本 FT は定数と capwords に焦点を当てる。

| API | ユースケース |
|---|---|
| `string.capwords(s)` | 単語の先頭を大文字化 |
| `string.ascii_letters` / `digits` / `punctuation` / `printable` | 文字集合定数 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft278-string/`

| 関数 | 概要 |
|---|---|
| `capwords_text()` | `string.capwords` で各単語を大文字化 |
| `classify_charset()` | string 定数で ASCII 文字種を判定 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/string/capwords` | 単語の先頭を大文字化 |
| POST | `/string/charset` | 文字種判定 |

---

## 摩擦点

### F-1: `capwords` は空白を畳む

**観察**: `string.capwords("a   b")` は `"A B"`（連続空白が 1 つに）。`str.title()` とは挙動が異なる（title はアポストロフィ等で誤動作する）。元の空白を保ちたい場合は不向き。

**対処**: capwords の空白畳み挙動を理解して使う。`"a   b"`→`"A B"` を確認。

### F-2: string 定数は ASCII 限定（ロケール非依存）

**観察**: `string.ascii_letters` は `a-zA-Z` のみで、ロケールに依存しない（昔の `string.letters` はロケール依存だった）。日本語等は含まれない。ASCII 限定の文字種チェックに適する。

**対処**: 集合演算（`set(text) <= _ASCII_ALNUM`）で ASCII 英数字のみか判定。日本語は `is_ascii_alnum=False`。ロケール非依存で安定。

### F-3: 文字種判定をセキュリティに使う場合

**観察**: ASCII 英数字のみの許可は、識別子・ファイル名・トークンの厳格化に使える（homoglyph FT246 の ASCII 限定対策とも整合）。ただし正当な非 ASCII 入力を弾く点に注意。

**対処**: 用途に応じて ASCII 限定を選択。本 FT は判定のみを提供。

---

## テスト結果

```
6 passed in 0.86s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

capwords は便利だが空白畳みは意外。string 定数は文字種チェックに使える。

**ドキュメント理解**: capwords の空白畳みをコメントで明示。
**事故リスク（低）**: 文字列処理のみ。
**規約の使いやすさ**: text → 結果が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

入力サニタイズで文字種チェックに使う。title() の罠を避け capwords を選べる。

**コピペ可能性**: classify_charset は流用可。
**拡張時の罠**: capwords の空白畳み・title との違い。
**事故リスク（低）**: ASCII 限定の理解。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

文字クラス（`/[a-z0-9]/`）の発想と一致。ロケール非依存は安心。

**エラーレスポンスの質**: 空は 422。
**Python 固有概念**: string 定数・capwords。
**事故リスク（低）**: 判定あり。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

ASCII 限定の文字種チェックは識別子・トークン検証で有用。homoglyph 対策（FT246）の ASCII 限定とも整合。

**他フレームワークとの差異**: 正規表現でも同等。string 定数は明示的。
**nene2 の薄さへの評価**: 集合演算による判定が明快。
**事故リスク（低）**: 判定のみ。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `str.title()` の誤動作を避け capwords/明示処理を使っているか。
- ASCII 限定チェックが正当な非 ASCII を不当に弾いていないか。
- 文字種チェックを homoglyph 対策（FT246）と組み合わせているか。
- 長さ上限。

**チームでの安全なパターン**: ASCII 限定は高セキュリティ識別子のみ、一般入力は NFKC + カテゴリ（FT246）。
**事故リスク（低）**: 判定を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。
**初心者でも安全な API 達成度**: ロケール非依存の ASCII 判定を提供。
**改善提案**: 文字種判定（本 FT）と NFKC/カテゴリ（FT246）の使い分けを how-to に統合する。
