# Field Trial 124: pathlib.Path + セキュアなファイル操作

## テーマ

`pathlib.Path` を使ったファイル操作で、パストラバーサル防止・拡張子バリデーション・
ディレクトリスキャン・MIME タイプ判定を FastAPI エンドポイントと組み合わせるパターンを検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft124-pathlib/` に以下を実装:

- `resolve_safe_path()` — `Path.resolve()` + `relative_to()` でパストラバーサルを防ぐ
- `ALLOWED_EXTENSIONS` — 許可拡張子セット、それ以外は 403
- `get_mime_type()` — `mimetypes.guess_type()` で MIME タイプを推定
- `GET /files` — ディレクトリスキャン（`glob("*")` / `glob("**/*")`）
- `GET /files/{filename:path}` — ファイル読み取り
- `POST /files/{filename:path}` — ファイル書き込み
- 13 テスト通過

## テスト結果

全 13 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `resolve()` + `relative_to()` でパストラバーサルを確実に防げる

```python
def resolve_safe_path(filename: str, base: Path) -> Path | None:
    try:
        resolved = (base / filename).resolve()
        resolved.relative_to(base.resolve())  # base の外なら ValueError
        return resolved
    except (ValueError, RuntimeError):
        return None
```

`Path("../etc/passwd").resolve()` は絶対パスに展開される。
`relative_to(base)` が `ValueError` を raise すれば `base` の外と判定できる。
`os.path.join` のような文字列操作より確実で、シンボリックリンクも `resolve()` で解決される。

### O2: FastAPI の `{filename:path}` でスラッシュを含むパスをキャプチャできる

```python
@app.get("/files/{filename:path}")
def read_file(filename: str) -> JSONResponse:
    ...

# GET /files/subdir/nested.txt → filename = "subdir/nested.txt"
```

`:path` コンバーターなしだと `/subdir/nested.txt` でルートがマッチしない。
パストラバーサルの実際の `../../` は URL エンコードや `resolve()` で対処する。

### O3: `mimetypes.guess_type()` でファイル拡張子から MIME タイプを推定できる

```python
mime, _ = mimetypes.guess_type("/path/to/file.json")
# → "application/json"
```

ファイルの内容を読まずに拡張子から MIME タイプを返せる。
不明な拡張子は `None` が返るので `"application/octet-stream"` にフォールバックする。

## まとめ

FT124 は摩擦ゼロ確認。CLAUDE.md の「ファイルパスは `pathlib.Path` で操作し、
パストラバーサルを防ぐ」ポリシーの正しい実装例として `resolve()` + `relative_to()` を確認した。
