# FT216: codecs モジュール — encode / decode / lookup / IncrementalEncoder

**日付**: 2026-05-23
**テーマ**: Python `codecs` モジュールの encode / decode / lookup / IncrementalEncoder の実装と検証
**セキュリティ診断**: あり（216 % 3 = 0）
**クラッカーペンテスト**: あり（216 % 4 = 0）

---

## 概要

`codecs` モジュールは Python のエンコーディング変換の基盤を提供する。今 FT では encode/decode/lookup/IncrementalEncoder の 4 機能を検証した。

| API | ユースケース |
|---|---|
| `str.encode(encoding, errors)` | テキスト → バイト列（codecs の動作を確認） |
| `bytes.decode(encoding, errors)` | バイト列 → テキスト |
| `codecs.lookup(encoding)` | コーデックのメタ情報取得 |
| `codecs.getincrementalencoder(encoding)()` | チャンク単位エンコード（ストリーミング処理向け） |
| エラーハンドラー | strict / ignore / replace / backslashreplace / xmlcharrefreplace |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft216-codecs/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `encode_text()` | テキストを指定エンコーディング・エラーハンドラーでバイト列に変換 |
| `decode_bytes()` | hex バイト列を指定エンコーディングでテキストに変換 |
| `lookup_codec()` | `codecs.lookup()` でコーデックのメタ情報を取得 |
| `incremental_encode()` | `IncrementalEncoder` でチャンク単位エンコードして往復確認 |
| `compare_error_handlers()` | 4 種類のエラーハンドラーの動作を比較 |
| `_validate_encoding()` | エンコーディング名のホワイトリスト検証 |
| `_validate_error_handler()` | エラーハンドラー名の検証 |

### エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/codecs/encode` | テキスト → バイト列エンコード |
| POST | `/codecs/decode` | バイト列 → テキストデコード |
| POST | `/codecs/lookup` | コーデックメタ情報取得 |
| POST | `/codecs/incremental-encode` | IncrementalEncoder チャンクエンコード |
| POST | `/codecs/error-handlers` | エラーハンドラー動作比較 |

---

## 摩擦点

### F-1: `codecs.encode()` / `codecs.decode()` の型注釈問題

**観察**: `codecs.encode(text, encoding, errors)` の戻り値型は `bytes | str` で、mypy は `bytes` への代入に `type: ignore` を要求する（Python のバージョンによって挙動が異なる）。

**対処**: Python 3.12 の mypy では `# type: ignore[assignment]` が "unused ignore" エラーになった。実際に `codecs.encode()` の代わりに `str.encode()` / `bytes.decode()` を使用することで型問題を回避し、コードをシンプルにした。`str.encode()` / `bytes.decode()` は内部的に `codecs` を呼んでいるため機能的に等価。

---

### F-2: `codecs` によるエンコーディング名の正規化

**観察**: `codecs.lookup("UTF-8")`, `codecs.lookup("utf_8")`, `codecs.lookup("utf-8")` はすべて同一コーデックを返す。しかし `_validate_encoding()` のホワイトリストは小文字ハイフン形式のみ保持している。

**対処**: `_validate_encoding()` で `encoding.lower().replace("_", "-")` に正規化してからホワイトリストと照合。ただし HTTP リクエストの `Literal` 型でエンコーディング名を制限しているため、実際には到達しないパスだが防御的に実装。

---

## セキュリティ診断結果

| カテゴリ | 項目 | 結果 |
|---|---|---|
| インジェクション | エンコーディング名に `rot_13` など非許可コーデック | 422（`Literal` 型で遮断） |
| インジェクション | エンコーディング名に path traversal（`../etc/passwd`） | 422（`Literal` 型で遮断） |
| 入力バリデーション | 10001 文字テキスト | 422（`max_length=MAX_TEXT_LENGTH` で遮断） |
| 入力バリデーション | 不正なエラーハンドラー名 | 422（`Literal` 型で遮断） |
| 入力バリデーション | 不正な hex データ（SQL injection 風） | 422（`bytes.fromhex()` で弾かれる） |
| 入力バリデーション | 巨大な hex_data | 422（`max_length=MAX_TEXT_LENGTH * 4` で遮断） |
| Unicode | RTL 文字をエンコーディング名に含む | 422（`Literal` 型が完全一致） |
| 情報漏洩 | 必須フィールド欠落時のスタックトレース | なし（422 の detail のみ） |
| Null バイト | テキスト内 null バイト | 200（null バイトは有効な UTF-8 として処理） |
| Infinity/NaN | float フィールドなし | 非該当（この FT は float 入力なし） |

**Null バイト（低リスク）**: `/codecs/encode` は `text` フィールドに null バイト（`\x00`）を受け入れ 200 を返す。UTF-8 では `\x00` は有効な文字なので制限不要。ただしバックエンドで C 言語関数に渡す場合は注意が必要（今 FT の用途では問題なし）。

**総合評価: 合格**

---

## クラッカーペンテスト結果

| 攻撃シナリオ | 結果 | 対処 |
|---|---|---|
| `rot_13` コーデック注入 | 422（`Literal` 型で遮断） | 対策済み |
| パストラバーサル in encoding name | 422（同上） | 対策済み |
| 不正なエラーハンドラー名 | 422（`Literal` 型で遮断） | 対策済み |
| 10001 文字のテキスト | 422（`max_length` で遮断） | 対策済み |
| SQL インジェクション風 hex_data | 422（`bytes.fromhex()` で弾かれる） | 対策済み |
| 巨大 hex_data（50001 バイト） | 422（`max_length` で遮断） | 対策済み |
| RTL 文字を含むエンコーディング名 | 422（`Literal` 型が完全一致） | 対策済み |
| 不正な UTF-8 バイト列を strict モードでデコード | 422（`UnicodeDecodeError` → ValidationException） | 対策済み |

**総合評価: 堅牢**

---

## テスト結果

```
24 passed in 0.40s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`encode` / `decode` は「テキスト ↔ バイト列」の変換として理解できる。エラーハンドラーの比較エンドポイントで `strict_error: true` と `ignore_result: "hello"` を対比することで「エンコードできない文字をどう処理するか」が視覚的に理解できる。

**ドキュメント理解**: BOM（Byte Order Mark）の概念は初心者には難しい。`utf-16` が `bom_included: true` を返す理由の説明が必要。

**事故リスク（中）**: `errors="ignore"` を使うと文字が無音で欠落する。「エンコードできない文字を無視して通す」ユースケースを理解せずに使うとデータロス。デフォルトを `strict` にしている設計は安全。

**規約の使いやすさ**: `Literal` 型でエンコーディング名とエラーハンドラーを制限しているため、補完が効く環境では入力しやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

エンコーディング変換はファイル入出力・Web スクレイピング・メール処理でよく使う。`cp932`（Shift-JIS 系）・`euc-jp` のサポートは実務で役立つ。

**コピペ可能性**: `encode_text` / `decode_bytes` パターンは CSV / テキストファイルの読み書きに直接流用できる。

**拡張時の罠**: `codecs.lookup()` の `codec_name` プロパティは正規化された名前を返す（`"utf-8"` → `"utf-8"`, `"UTF8"` → `"utf-8"`）。`IncrementalEncoder` はマルチバイト文字をチャンクで分割すると文字境界をまたぐ可能性があり、日本語の UTF-8 でチャンクサイズ 1 を試すと確認できる（今 FT では往復確認で検証済み）。

**事故リスク（低）**: ホワイトリスト検証とエラーハンドラーの明示的指定で安全。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS の `TextEncoder` / `TextDecoder` Web API と対応している。`TextEncoder` は常に UTF-8 だが、Python の `codecs` は多様なエンコーディングをサポートする点が異なる。

**エラーレスポンスの質**: `UnicodeEncodeError` / `UnicodeDecodeError` を 422 に変換して `{field, message, code}` 形式で返すため、フロントエンドが原因を特定できる。

**Python 固有概念**: `IncrementalEncoder` はストリーミング処理用で、ブラウザの `ReadableStream` の概念に近い。チャンクを逐次処理して `final=True` で最終化する流れは直感的。

**事故リスク（低）**: `Literal` 型で入力を制約しており、不正なエンコーディング名は 422 で拒否される。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `FileResponse` や `StreamingHttpResponse` は内部で `codecs` を使う。`IncrementalEncoder` は大きなファイルのストリーミングエンコードに有効。

**他フレームワークとの差異**: nene2 のデモアプリは `codecs` を HTTP API でラップしているが、実際の利用場面は「レガシーシステムとのエンコーディング変換」や「バイナリプロトコルの処理」。API 設計として hex 入出力を選択したことで、バイナリデータをそのまま JSON で扱える。

**nene2 の薄さへの評価**: `_validate_encoding()` のホワイトリストは CLAUDE.md のセキュリティポリシーに沿っており、`codecs.lookup()` に任意の文字列を渡すリスクを排除している。

**事故リスク（低）**: エンコーディングとエラーハンドラーが `Literal` 型で制約され、二重バリデーションで堅牢。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- エンコーディング名はユーザー入力か定数か — ユーザー入力の場合は必ずホワイトリスト検証（`codecs.lookup()` は任意の文字列を受け入れる）
- `errors="ignore"` は意図的な選択か — データロスが許容されるユースケースかを確認
- BOM 付きエンコーディング（`utf-16`, `utf-32`）を使う場合、後段の処理で BOM を考慮しているか
- `IncrementalEncoder` は `final=True` で確定化しているか — 未確定のバッファが残るとデータ欠落

**チームでの安全なパターン**: エンコーディング名を `Literal` 型で制限し、`_validate_encoding()` でバリデーションするパターンは再利用可能。

**事故リスク（低）**: セキュリティ診断・クラッカーペンテスト両方合格。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: エンコーディング名と errors ハンドラーの `Literal` 型制約は CLAUDE.md のセキュリティポリシー（外部入力の全バリデーション）に準拠。`frozen=True, slots=True` のレスポンス dataclass も標準に準拠。

**初心者でも安全な API 達成度**: デフォルトを `errors="strict"` にすることで、無音のデータロスを防ぐ安全なデフォルト設計。`xmlcharrefreplace_result` で HTML エンティティ参照への変換を可視化することで、Web 出力のエスケープ概念の学習にも役立つ。

**改善提案**: `codecs.encode()` の代わりに `str.encode()` を使った点は実装上の合理的選択だが、FT のテーマが `codecs` モジュールである以上、`codecs.open()` や `codecs.StreamReader/Writer` などの上位 API も将来の FT で検証する価値がある。
