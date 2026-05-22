# FT214: io モジュール — StringIO / BytesIO / TextIOWrapper / BufferedReader

**日付**: 2026-05-22
**テーマ**: Python `io` モジュールの StringIO / BytesIO / TextIOWrapper / BufferedReader の実装と検証
**セキュリティ診断**: なし（214 % 3 = 2）
**クラッカーペンテスト**: なし（214 % 4 = 2）

---

## 概要

`io` モジュールは Python のストリーム I/O の基盤を提供する。今 FT では 4 つの主要クラスを HTTP API で検証した。

| API | ユースケース |
|---|---|
| `StringIO` | メモリ上のテキストバッファ（ファイルライクな読み書き・行イテレーション） |
| `BytesIO` | メモリ上のバイナリバッファ（バイト列の書き込み・デコード） |
| `TextIOWrapper` | バイナリストリームをテキストストリームに変換（エンコーディング制御） |
| `BufferedReader` | バッファリング付きバイナリ読み取り（シーク操作） |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft214-io/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `process_text_stream()` | `StringIO` にテキスト行を書き込み・読み返して文字数・行数を返す |
| `iterate_lines()` | `StringIO` をファイルのようにイテレーションして行リストを返す |
| `process_byte_stream()` | `BytesIO` にバイト列を書き込み・デコードして hex preview を返す |
| `encode_decode_roundtrip()` | `TextIOWrapper` で指定エンコーディングの往復変換を確認する |
| `seek_operations()` | `BufferedReader` + `TextIOWrapper` でシーク操作を検証する |

### エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/io/text-stream` | StringIO テキストストリーム書き込み・読み取り |
| POST | `/io/line-iter` | StringIO 行イテレーション |
| POST | `/io/byte-stream` | BytesIO バイナリストリーム操作 |
| POST | `/io/encoding` | TextIOWrapper エンコーディング変換往復確認 |
| POST | `/io/seek` | BufferedReader + TextIOWrapper シーク操作 |

---

## 摩擦点

### F-1: `StringIO.tell()` はシーク位置を返す（文字数ではない）

**観察**: `buffer.tell()` で「書き込んだ文字数」を取得しようとすると、シーク後の現在位置が返る。

```python
with io.StringIO() as buffer:
    buffer.write("abc\n")   # 4 文字書き込み
    char_count = buffer.tell()  # → 4（書き込み後の位置 = 文字数）
    buffer.seek(0)
    content = buffer.read()
    # この時点で buffer.tell() は content の長さと等しい（EOF 位置）
```

`buffer.tell()` のタイミングによって返る値が変わるため、「書き込み後すぐ tell()」して文字数を記録し、seek(0) / read() の後は「コンテンツ長と同じ値」になることをテストで確認した。初期実装では「read() 後に tell() == 0」と誤って期待し、テストが失敗した。

**対処**: `char_count = buffer.tell()` を `seek(0)` の前に呼ぶ。read() 後の tell() は EOF 位置（= content 長）になることを理解した上でテストを修正。

---

### F-2: `TextIOWrapper` は `write_through=True` が必要

**観察**: `BytesIO` を `TextIOWrapper` でラップして書き込む場合、バッファリングのために `getvalue()` が空になることがある。

```python
byte_buffer = io.BytesIO()
wrapper = io.TextIOWrapper(byte_buffer, encoding="utf-8")
wrapper.write("hello")
byte_buffer.getvalue()  # → b'' （バッファがフラッシュされていない）
```

**対処**: `write_through=True` を指定するか、`flush()` を明示的に呼ぶことで確実にバイト列が BytesIO に書き込まれる。

```python
with io.TextIOWrapper(byte_buffer, encoding=encoding, write_through=True) as wrapper:
    wrapper.write(text)
    encoded_bytes = byte_buffer.getvalue()  # ← write_through=True で即座に反映
```

---

## テスト結果

```
22 passed in 0.42s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`StringIO` は「テキストをファイルとして扱える in-memory バッファ」という説明が直感的。ファイル読み書きを学ぶ前にメモリ上で練習できる点で教育的。

**ドキュメント理解**: `tell()` の挙動（シーク位置を返す）は初心者には不明瞭。「文字数を取得するには seek(0) の前に tell() を呼ぶ」という順序依存性は文書化が必要。

**事故リスク（中）**: `TextIOWrapper` を閉じると内包する `BytesIO` も閉じられる。`with` ブロックを抜けた後に `BytesIO.getvalue()` を呼ぶ必要があり、`with` ブロック内で `getvalue()` を取得するか、`BytesIO` の参照を外部で保持する必要がある。

**規約の使いやすさ**: コンテキストマネージャ（`with io.StringIO() as buffer:`）は Python の標準パターンとして自然。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`StringIO` はテストでファイル I/O をモックするのに頻繁に使う。`BytesIO` は画像・PDF の処理でよく登場する。`TextIOWrapper` でのエンコーディング変換は実務的に有用。

**コピペ可能性**: `process_byte_stream` / `encode_decode_roundtrip` のパターンは画像バイト列 → レスポンス変換などに直接応用できる。

**拡張時の罠**: `TextIOWrapper` は `close()` 時に内包ストリームも閉じる。外部の `BytesIO` を再利用したい場合は `closefd=False` や事前に `getvalue()` する必要がある。

**事故リスク（低）**: エンコーディングの検証を `Literal` 型で行うため、サポート外エンコーディングは 422 で遮断。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

Node.js の `Buffer` クラスと類似した概念。JS の `Uint8Array` / `TextDecoder` に対応する。`StringIO` は `ReadableStream` に近い感覚で理解できる。

**エラーレスポンスの質**: `UnicodeEncodeError` を 422 に変換して `{field, message, code}` で返すため、フロントエンドがエンコーディングエラーを適切に処理できる。

**Python 固有概念**: `seek()` の単位がバイト（`BufferedReader`）か文字（`StringIO`）かがストリーム種別によって異なる点は学習コストあり。

**事故リスク（低）**: `Literal` 型によるエンコーディング名の制約で無効なエンコーディングは 422。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `InMemoryUploadedFile` や `ContentFile` は内部で `BytesIO` / `StringIO` を使う。`TextIOWrapper` のエンコーディング変換はファイルアップロード処理でよく使うパターン。

**他フレームワークとの差異**: nene2 のデモアプリは io ストリームを HTTP API でラップしているが、実際の利用場面は「メモリ上でのファイル処理」や「テスト用モック」が主流。API のデモとして適切。

**nene2 の薄さへの評価**: `Literal["utf-8", "utf-16", "latin-1", "ascii"]` でエンコーディングを制限している点は実用的。本番では `chardet` などで動的検出も検討できる。

**事故リスク（低）**: バリデーションが Pydantic + 手動チェックで二重保護。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `TextIOWrapper` を `with` 文で使う場合、内包する `BytesIO` が閉じられるタイミングに注意（`getvalue()` は with ブロック内で呼ぶ）
- `StringIO.tell()` のタイミング依存性 — 書き込み後すぐ呼ぶか、EOF 位置として解釈するかを明確に
- `write_through=True` を使わない場合、明示的 `flush()` が必要

**チームでの安全なパターン**: `encode_decode_roundtrip` の `roundtrip_ok` フラグで変換の往復確認をする設計は堅牢。エンコーディングミスを早期検出できる。

**事故リスク（低）**: 入力バリデーションが Pydantic + Literal 型で徹底されており安全。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `Literal` 型でエンコーディングを制限するパターンは FT211/FT213 から継続しており一貫性がある。`frozen=True, slots=True` のレスポンス dataclass も標準に準拠。

**初心者でも安全な API 達成度**: `hex_data` フィールドに `max_length=MAX_BYTE_LENGTH * 2` を設定（hex 文字は 1 バイトあたり 2 文字）。バイト列長の制限が適切に変換されている。

**改善提案**: `TextIOWrapper` の `closefd` / `write_through` など非自明なパラメータは、デモコードに短いコメントを添えると初心者の理解を助ける（ただし CLAUDE.md の「コメントは WHY のみ」ポリシーに従い、非自明な理由がある場合のみ）。
