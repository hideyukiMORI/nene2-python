# FT217: csv モジュール — reader / writer / DictReader / DictWriter / Sniffer

**日付**: 2026-05-23
**テーマ**: Python `csv` モジュールの reader / writer / DictReader / DictWriter / Sniffer の実装と検証
**セキュリティ診断**: なし（217 % 3 = 1）
**クラッカーペンテスト**: なし（217 % 4 = 1）

---

## 概要

`csv` モジュールは Python でテーブル形式データを扱う標準的な方法を提供する。今 FT では reader / writer / DictReader / DictWriter / Sniffer の 5 API を検証した。

| API | ユースケース |
|---|---|
| `csv.reader` | CSV テキスト → `list[list[str]]`（行のリスト） |
| `csv.writer` | `list[list[str]]` → CSV テキスト |
| `csv.DictReader` | ヘッダー行付き CSV → `list[dict[str, str]]` |
| `csv.DictWriter` | `list[dict[str, str]]` → ヘッダー付き CSV |
| `csv.Sniffer` | CSV の区切り文字とヘッダー有無を自動検出 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft217-csv/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `read_csv()` | `csv.reader` で CSV テキストを行リストにパース |
| `write_csv()` | `csv.writer` で行リストを CSV テキストに変換 |
| `read_csv_dict()` | `csv.DictReader` でヘッダー付き CSV を辞書リストに変換 |
| `write_csv_dict()` | `csv.DictWriter` で辞書リストをヘッダー付き CSV に変換 |
| `sniff_csv()` | `csv.Sniffer` で区切り文字とヘッダー有無を推定 |
| `_validate_csv_length()` | CSV テキストの長さ上限チェック |
| `_validate_field()` | フィールド値の長さ上限チェック |

### エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/csv/read` | CSV テキスト → 行リスト |
| POST | `/csv/write` | 行リスト → CSV テキスト |
| POST | `/csv/dict-read` | CSV テキスト → 辞書リスト（ヘッダーあり） |
| POST | `/csv/dict-write` | 辞書リスト → CSV テキスト（ヘッダーあり） |
| POST | `/csv/sniff` | CSV 区切り文字・ヘッダー有無を推定 |

---

## 摩擦点

### F-1: `csv.Sniffer.sniff()` の `dialect.quotechar` が `str | None`

**観察**: `csv.Sniffer.sniff()` が返す `dialect.quotechar` の型注釈は `str | None` で、mypy strict では `SnifferResult(quotechar=dialect.quotechar)` がエラーになる（`SnifferResult.quotechar` は `str` 型）。

**対処**: `dialect.quotechar or '"'` でフォールバック値を指定。quotechar が None になるのは区切り文字が検出できなかった場合（`csv.Error` が発生する前段階）であり、実際には到達しにくいパスだが mypy の型安全のためにフォールバックを実装。

---

### F-2: `Literal` 型で区切り文字を制限するとタブ文字の扱いが複雑

**観察**: `delimiter: Literal[",", ";", "\t", "|"]` とした場合、JSON リクエストボディで `"delimiter": "\t"` を送ると Pydantic が正しく `\t` として解釈する。一方、テスト側で `json={"delimiter": "\t"}` を使うと Python の JSON エンコーダーが `\t` をそのまま送るため動作する。

**対処**: `Literal` 型で制限する方針はそのまま維持。`\t` は JSON のエスケープシーケンスとして正規の表現であり、問題なし。

---

## テスト結果

```
25 passed in 0.32s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`csv.reader` / `csv.writer` は「テキスト ↔ リスト」の変換として直感的に理解できる。DictReader の「1 行目がヘッダー」という概念も、エンドポイントのレスポンスで `fieldnames` が分離されているため視覚的に把握できる。

**ドキュメント理解**: Sniffer の「自動検出」は便利だが、誤検出の可能性（特に短い CSV や 1 列データ）を説明する必要がある。

**事故リスク（中）**: `csv.writer` は区切り文字を含むフィールドを自動的にクォートするが、読み手がその仕様を知らないと「なぜダブルクォートが付くのか」と混乱する可能性がある。デフォルト `delimiter=","` とクォート動作の説明があれば安心。

**規約の使いやすさ**: `Literal` 型で `","`, `";"`, `"\t"`, `"|"` の 4 種類に制限しているため、使用可能な区切り文字が明確。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

CSV は日常業務のデータ交換フォーマットとして頻用される。`DictReader` / `DictWriter` パターンはスプレッドシートデータの読み書きに直接流用できる。

**コピペ可能性**: `read_csv_dict` → 処理 → `write_csv_dict` のパターンは ETL（Extract/Transform/Load）処理の雛形として使いやすい。

**拡張時の罠**: `csv.Sniffer` は入力データが十分な行数・バリエーションを持つ場合に正確に動作する。1〜2 行の CSV や全列が同一値の CSV では誤検出する。`sample=csv_text[:4096]` で先頭 4096 文字のみ解析しているため、大きなファイルでも効率的。

**事故リスク（低）**: フィールド長とテキスト長の上限検証を実装しているため、大量データの DoS に強い。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`csv.reader` は JS の `Papa.parse()` に相当する。DictReader は `{ header: true }` オプション相当の動作。

**エラーレスポンスの質**: 不正な区切り文字は Pydantic の `Literal` 型で 422 を返す。`csv.Error` は `ValidationException` に変換されて `{field, message, code}` 形式で返るため、フロントエンドが CSV 解析エラーの原因を特定できる。

**Python 固有概念**: `csv.Sniffer` はブラウザ側の `FileReader` と組み合わせると便利。ファイルアップロード後に先頭部分だけ送信して区切り文字を自動検出し、その後の処理パラメータを確定するフローに活用できる。

**事故リスク（低）**: `Literal` 型と長さ制限で入力を制約。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django では `csv.DictWriter` を使ったダウンロードレスポンス（`StreamingHttpResponse` + ジェネレーター）が典型的なパターン。今 FT は文字列バッファでの処理だが、大規模データではストリーミングへの移行が必要。

**他フレームワークとの差異**: nene2 の実装は CSV を文字列として往復させるため、メモリに全データを保持する。実際の本番ユースケースでは `io.BytesIO` + `StreamingResponse` を使ったチャンク転送が推奨される（FT214 io モジュールの知見と組み合わせ可能）。

**nene2 の薄さへの評価**: `read_csv` / `write_csv` の薄いラッパーは必要最低限で、ビジネスロジックを含まないデモとして適切。CSV の行上限（1000 行）やフィールド長上限（500 文字）は本番ユースケースに合わせて調整できる設計。

**事故リスク（低）**: 入力検証が二重（Pydantic + `_validate_rows`）になっており堅牢。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `csv.Sniffer` を本番コードで使う場合は誤検出時のフォールバック処理が必要（今 FT は `csv.Error` を 422 に変換）
- `DictWriter` で `fieldnames` にない key を持つレコードを渡すと `ValueError` が発生する — 今 FT は `_validate_records` でチェックしていないが、Pydantic の型制約（`dict[str, _BoundedStr]`）と `DictWriter` の extrasaction デフォルト（`raise`）で実質保護されている
- CSV インジェクション（フォーミュラインジェクション）: セル先頭の `=`, `+`, `-`, `@` はスプレッドシートアプリで数式として実行される可能性がある — 今 FT はデモスコープのため未対応だが、エンドユーザーがスプレッドシートに取り込む場合は要注意

**チームでの安全なパターン**: `Literal` 型で区切り文字を制限し、`max_length` でテキスト・フィールド長を上限制御するパターンは再利用可能。

**事故リスク（低）**: 入力バリデーション・例外変換が整合している。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `Literal` 型での入力制限・`max_length` 制約・`frozen=True, slots=True` のレスポンス dataclass はすべて CLAUDE.md ポリシーに準拠。`csv.reader` / `csv.writer` は副作用がなく、HTTP ハンドラーが薄い「parse → use-case → response」3 ステップに収まっている。

**初心者でも安全な API 達成度**: `Literal` 型での区切り文字制限は「任意の文字を渡せない」明確な境界を提供する。デフォルト `delimiter=","` も直感的。

**改善提案**: CSV インジェクション（フォーミュラインジェクション）対策は今 FT スコープ外だが、企業データをスプレッドシートへエクスポートするユースケースでは将来の FT で検証する価値がある（`=HYPERLINK(...)` などの悪意あるセル値の無害化）。
