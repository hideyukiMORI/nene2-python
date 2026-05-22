# FT218: configparser モジュール — read / write / sections / interpolation

**日付**: 2026-05-23
**テーマ**: Python `configparser` モジュールの read / write / sections / interpolation の実装と検証
**セキュリティ診断**: なし（218 % 3 = 2）
**クラッカーペンテスト**: なし（218 % 4 = 2）

---

## 概要

`configparser` モジュールは Python で INI 形式の設定ファイルを読み書きする標準的な手段を提供する。今 FT では read / write / sections / interpolation の 4 側面を検証した。

| API | ユースケース |
|---|---|
| `ConfigParser.read_string()` | INI テキスト → セクション辞書 |
| `ConfigParser.write()` | セクション辞書 → INI テキスト |
| `sections()` / `has_section()` / `has_option()` / `get()` | セクション・オプション操作 |
| `BasicInterpolation` | `%(key)s` 形式の変数展開 |
| `DEFAULT` セクション | 全セクションに継承されるデフォルト値 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft218-configparser/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `parse_ini()` | `ConfigParser.read_string()` で INI テキストをセクション辞書にパース |
| `write_ini()` | セクション辞書と DEFAULT を INI テキストに変換 |
| `get_value()` | セクション・キーで値を取得（存在チェック付き） |
| `interpolate_value()` | `%(key)s` 形式の補間前後の値を比較 |
| `_make_parser()` | `interpolation=None` または `BasicInterpolation()` を使い分け |
| `_validate_ini_length()` / `_validate_key()` / `_validate_value()` | 入力長検証 |

### エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/configparser/parse` | INI テキスト → セクション辞書 |
| POST | `/configparser/write` | セクション辞書 → INI テキスト |
| POST | `/configparser/get` | セクションとキーで値を取得 |
| POST | `/configparser/interpolate` | 補間前後の値を比較 |

---

## 摩擦点

### F-1: `configparser.DuplicateSectionError` が mypy strict で警告なく送出される

**観察**: `read_string()` に重複セクション（`[section1]` が 2 回）を渡すと `configparser.DuplicateSectionError`（`configparser.Error` のサブクラス）が発生する。これは想定内だが、`parse_ini()` の `try-except` で `configparser.Error` を捕捉し 422 に変換する必要がある。

**対処**: ハンドラー側で `except (ValueError, configparser.Error)` を使い、`configparser.Error` を `ValidationException` に変換。重複セクションは 422 で返る（テストで検証済み）。

---

### F-2: `interpolation=None` の型注釈と `BasicInterpolation` の使い分け

**観察**: `configparser.ConfigParser(interpolation=None)` で補間を無効化できるが、mypy では `interpolation` パラメータの型が `Interpolation | None` であるため、`None` 渡しは正式なインターフェース。一方 `BasicInterpolation()` は `%(key)s` 形式の変数展開のみサポートし、`%(key)s` 以外のパターン（例: `${key}`）は展開しない。

**対処**: `_make_parser(interpolation: bool)` で使い分けを明示。同じ INI テキストを raw と interpolated の 2 パーサーで解析し、補間前後の値を両方返すことで差分を可視化。

---

## テスト結果

```
19 passed in 0.32s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`configparser` は「INI ファイルを読み書きするモジュール」として理解できる。`[section]` / `key = value` の文法は視覚的に分かりやすい。`DEFAULT` セクションが全セクションに継承される仕様は少し直感に反するかもしれない。

**ドキュメント理解**: `%(key)s` の補間記法は Python の旧式フォーマット文字列に似ているが、configparser 専用の文法として別個に説明が必要。

**事故リスク（低）**: 重複セクションが 422 に変換されるため、不正な INI テキストがサイレントに通ることはない。デフォルト `interpolation=None` で `%(key)s` を含む値もそのまま返るため、誤って展開される事故もない。

**規約の使いやすさ**: INI テキストを文字列として POST する API 設計は直感的。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

設定ファイルの読み書きは実務でよく使う。`parse_ini` / `write_ini` の往復（roundtrip テストで検証）はコピペベースで使いやすい。

**コピペ可能性**: `write_ini` → `parse_ini` の roundtrip パターンはコンフィグ移行スクリプトに直接流用できる。

**拡張時の罠**: `configparser` はデフォルトでキーを小文字に変換する（`optionxform = str.lower`）。大文字小文字を保持したい場合は `parser.optionxform = str` を設定する必要がある（今 FT 未対応、用途によっては摩擦点になる）。

**事故リスク（低）**: 入力長検証とエラー変換で安全。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

INI 形式は TOML / YAML に比べてシンプルで、機能限定アプリの設定ファイルに向く。

**エラーレスポンスの質**: `DuplicateSectionError` を 422 に変換して `{field, message, code}` 形式で返すため、クライアントが原因を特定できる。

**Python 固有概念**: `%(key)s` の補間は Python 2 時代の `%` フォーマットの名残。JS 開発者には「テンプレートリテラルの限定版」として説明すると分かりやすい。

**事故リスク（低）**: `interpolation=None` をデフォルトにすることで、補間の意図しない展開を防いでいる。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `settings.py` は configparser を使わないが、`django.conf.global_settings` と概念的に対応する。`DEFAULT` セクションの継承は Django の `DATABASES['default']` に近い思想。

**他フレームワークとの差異**: nene2 の実装は INI テキストを HTTP API でラップしており、ファイルシステムへのアクセスを伴わない。本番では `read_string(Path("config.ini").read_text())` の形で使うケースが多い。

**nene2 の薄さへの評価**: `_make_parser()` ファクトリ関数で `interpolation` の有無を切り替える設計は明確。`interpolation=None` デフォルトで安全。

**事故リスク（低）**: 二重バリデーション（Pydantic + `_validate_*`）で堅牢。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `configparser` のキーは小文字変換される — 大文字キーを期待するコードは `optionxform = str` の設定が必要
- `BasicInterpolation` の `%(key)s` は再帰展開される可能性がある — 深くネストした補間は `InterpolationDepthError` を発生させる（今 FT では `configparser.Error` でキャッチ済み）
- `DEFAULT` セクションの値はすべてのセクションで継承される — 意図しない値の漏れ込みに注意
- `configparser` は型情報を持たない（すべて文字列）— 型変換は `getint()` / `getboolean()` を使う

**チームでの安全なパターン**: `interpolation=None` と `BasicInterpolation` を明示的に切り替える `_make_parser()` パターンは再利用可能。

**事故リスク（低）**: エラー変換が整合している。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `Pydantic` での入力検証・`frozen=True, slots=True` の dataclass・`ValidationException` への例外変換はすべてポリシー準拠。`interpolation=None` デフォルトでセキュアな設計。

**初心者でも安全な API 達成度**: `parse` / `write` / `get` / `interpolate` の 4 エンドポイントで configparser の主要機能を網羅。補間前後の値を両方返す `interpolate` エンドポイントは学習目的として有用。

**改善提案**: `configparser` のキー小文字変換（`optionxform`）と `getint()` / `getboolean()` / `getfloat()` の型付き取得メソッドは将来の FT で検証する価値がある。
