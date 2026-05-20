# FT162: zipfile モジュール

**日付**: 2026-05-21
**テーマ**: `zipfile` モジュール — ZipFile 読み書き、圧縮方式比較、インメモリ ZIP、ファイル追記、メタデータ検査

---

## 概要

Python 標準ライブラリの `zipfile` モジュールを nene2-python フレームワーク上で検証した。
`zipfile` は ZIP アーカイブの作成・読み取り・更新を提供するモジュールで、
`io.BytesIO` と組み合わせることでファイルシステムへの書き込みなしに
インメモリで ZIP を扱えることが特徴。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft162-zipfile/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `create_zip_bytes(files)` | `io.BytesIO` でインメモリ ZIP を作成 |
| `read_zip_contents(zip_bytes)` | ZIP を読み取り namelist/infolist/内容を返す |
| `compare_compression(content)` | ZIP_STORED vs ZIP_DEFLATED の圧縮比を比較 |
| `zip_roundtrip(files)` | 作成→展開のラウンドトリップ検証 |
| `append_to_zip(initial, new)` | 既存 ZIP にファイルを追記 (`mode="a"`) |
| `inspect_zip(files)` | `is_zipfile()` / `ZipInfo` でメタデータを検査 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/zip/create` | ZIP をインメモリで作成してバイナリ返却 |
| POST | `/zip/roundtrip` | ラウンドトリップ検証 |
| POST | `/zip/compress-compare` | 圧縮方式の比較 |
| POST | `/zip/append` | 既存 ZIP にファイルを追記 |
| POST | `/zip/inspect` | ZIP メタデータを検査 |

---

## テスト結果

**25 passed（摩擦ゼロ）**

```
25 passed in 0.70s
```

---

## 摩擦ポイント

**今回の FT では実装上の摩擦はゼロだった。**

---

## 観察点

### 観察1: `io.BytesIO` との組み合わせで完全インメモリ処理が可能

```python
buf = io.BytesIO()
with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("hello.txt", "Hello, World!")
zip_bytes = buf.getvalue()
```

Web サービスでは一時ファイルを作成せずにメモリ上で ZIP を生成・返却できる。
`buf.getvalue()` で ZIP の全バイト列を取得し `Response(content=..., media_type="application/zip")` で返す。

### 観察2: `writestr()` vs `write()`

- `zf.writestr(name, data)`: 文字列・bytes を直接 ZIP エントリとして書き込む（ファイル不要）
- `zf.write(filename, arcname)`: 既存ファイルを ZIP に追加

Web サービスではファイルシステムに保存せずに処理できる `writestr()` の方が適している。

### 観察3: 圧縮方式の選択

| 定数 | 説明 | 用途 |
|---|---|---|
| `ZIP_STORED` | 無圧縮 | 高速、すでに圧縮済みのファイル |
| `ZIP_DEFLATED` | zlib 圧縮 | 汎用（デフォルト的に使われる） |
| `ZIP_BZIP2` | bzip2 圧縮 | より高い圧縮率 |
| `ZIP_LZMA` | LZMA 圧縮 | 最高圧縮率、低速 |

繰り返しの多いテキストファイルでは DEFLATED により 80% 以上の圧縮が得られる。

### 観察4: `mode="a"` で既存 ZIP への追記が可能

```python
buf = io.BytesIO(existing_zip_bytes)
with zipfile.ZipFile(buf, mode="a") as zf:
    zf.writestr("new_file.txt", "new content")
```

`mode="a"` は既存の ZIP アーカイブにエントリを追加する。
同名エントリを追加すると ZIP 内に重複エントリが発生するため注意。
（最後に追加されたエントリが `read()` で読まれる）

### 観察5: `ZipInfo` でメタデータにアクセス

`zf.infolist()` は `ZipInfo` オブジェクトのリストを返す:
- `info.filename`: エントリ名
- `info.file_size`: 展開後のサイズ
- `info.compress_size`: 圧縮後のサイズ
- `info.date_time`: タプル `(year, month, day, hour, min, sec)`
- `info.compress_type`: 圧縮方式

### 観察6: `zipfile.is_zipfile()` でバリデーション

```python
zipfile.is_zipfile(path_or_buf)  # bool
```

ファイルパスまたはファイルライクオブジェクトを受け取り、
ZIP ファイルかどうかを判定する。
ユーザーアップロードファイルの検証に使える。
`io.BytesIO` を渡した後は `seek(0)` が必要な点に注意。

---

## nene2-python フレームワークとの統合

- ZIP バイナリ返却は `Response(content=..., media_type="application/zip")` を使用
- `JSONResponse` との混在も問題なし
- Pydantic BodyModel でファイル辞書のサイズを `max_length=50` で制限
- 圧縮フォーマット文字列は `pattern` フィールドで正規表現バリデーション

---

## まとめ

`zipfile` は `io.BytesIO` との組み合わせで Web サービスに適したインメモリ ZIP 処理が可能。
`writestr()`, `namelist()`, `infolist()`, `is_zipfile()` などの API が直感的で、
バックアップ、配布物生成、アップロードファイル検証など幅広い用途に使える。
摩擦ゼロで実装完了。
