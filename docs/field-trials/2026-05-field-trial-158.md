# Field Trial 158: tempfile モジュール

## テーマ

`tempfile.NamedTemporaryFile`, `TemporaryDirectory`, `SpooledTemporaryFile`,
`mkdtemp`, `gettempdir` を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft158-tempfile/` に以下を実装:

- `write_read_temp_file()` — `NamedTemporaryFile` に書いて読んで自動削除を確認
- `temp_file_persist()` — `delete=False` で閉じた後も残ることを確認
- `use_temp_directory()` — `TemporaryDirectory` でファイルを作成してコンテキスト終了で削除確認
- `mkdtemp_demo()` — `mkdtemp` で prefix/suffix 付きディレクトリを作成
- `spooled_file_demo()` — `SpooledTemporaryFile` でメモリ/ファイルの自動切り替えを確認
- `get_temp_dir_info()` — `gettempdir()` でシステムのテンポラリディレクトリを取得
- HTTP エンドポイント 6 本
- 26 テスト全通過（摩擦1件）

## テスト結果

初回: 5 失敗 → 修正後: 26 テスト全通過。

## Friction Points

### FP1: `NamedTemporaryFile(mode="w")` は書き込み専用で `read()` 不可

```python
# NG: mode="w" は書き込み専用
with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as tmp:
    tmp.write("hello")
    tmp.flush()
    tmp.seek(0)
    tmp.read()  # → io.UnsupportedOperation: not readable
```

`mode="w"` は書き込み専用のため `read()` が `io.UnsupportedOperation` を送出する。
書いて同一ファイルハンドルで読み返すには `mode="w+"` が必要。

**対処**: `mode="w+"`（読み書き両用）に変更した。

```python
with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8") as tmp:
    tmp.write("hello")
    tmp.flush()
    tmp.seek(0)
    tmp.read()  # OK
```

## 観察

### O1: `NamedTemporaryFile` はデフォルトで閉じると自動削除される

```python
with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8") as tmp:
    tmp.write("hello")
    name = tmp.name

os.path.exists(name)  # → False (自動削除)
```

`delete=False` にすると閉じた後も残る。その場合は呼び出し元が削除する責任を持つ。

### O2: `TemporaryDirectory` はコンテキスト終了でディレクトリごと削除する

```python
with tempfile.TemporaryDirectory() as tmpdir:
    Path(tmpdir, "file.txt").write_text("hello")
    # tmpdir は有効なディレクトリ

os.path.exists(tmpdir)  # → False (ディレクトリごと削除)
```

`pathlib.Path(tmpdir)` で `pathlib` と組み合わせて使いやすい。

### O3: `mkdtemp` は削除を呼び出し元が責任を持つ

```python
tmpdir = tempfile.mkdtemp(prefix="myapp_", suffix="_work")
# → "/tmp/myapp_abc123_work" のような名前のディレクトリが作成される

# 必ず後片付けが必要
import shutil
shutil.rmtree(tmpdir)
```

`TemporaryDirectory` と違い自動削除しないため、例外処理と組み合わせて確実に削除する。

### O4: `SpooledTemporaryFile` は閾値までメモリ、超えたらファイルに保存する

```python
with tempfile.SpooledTemporaryFile(max_size=1024, mode="w+", encoding="utf-8") as spooled:
    spooled.write("small content")  # メモリに保持
    spooled.write("x" * 10000)     # max_size を超えたらファイルに自動切り替え
    spooled.seek(0)
    data = spooled.read()           # どちらの場合も透過的に読める
```

ストリーミングアップロードや一時的なバッファリングに使いやすい。
コンテキスト終了で自動削除（`NamedTemporaryFile` と同様）。

### O5: `gettempdir()` はシステムのテンポラリディレクトリを返す

```python
tempfile.gettempdir()  # Linux: "/tmp", Windows: "C:\\Users\\...\\AppData\\Local\\Temp"
```

環境変数 `TMPDIR`, `TEMP`, `TMP` の順に参照し、なければプラットフォーム固定の場所を返す。

## まとめ

FT158 は摩擦1件（`NamedTemporaryFile(mode="w")` で `read()` 不可）。
`NamedTemporaryFile` / `TemporaryDirectory` はコンテキストマネージャで自動削除、
`mkdtemp` は手動削除が必要。
`SpooledTemporaryFile` はメモリとファイルを透過的に切り替えるため
一時的なストリーミングバッファに有用。
