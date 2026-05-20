# Field Trial 159: fnmatch と glob モジュール

## テーマ

`fnmatch.fnmatch/fnmatchcase/filter/translate`,
`glob.glob/iglob/escape`, `pathlib.Path.glob` を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft159-fnmatch-glob/` に以下を実装:

- `match_pattern()` — `fnmatch.fnmatch()` でワイルドカードパターンマッチ
- `match_pattern_case()` — `fnmatch.fnmatchcase()` で常に大文字小文字を区別
- `filter_names()` — `fnmatch.filter()` でリストを絞り込む
- `translate_pattern()` — `fnmatch.translate()` でパターンを正規表現に変換
- `glob_in_temp_dir()` — 一時ディレクトリで `glob.glob()` を検証
- `pathlib_glob_demo()` — `pathlib.Path.glob()` で同じ操作を検証
- `glob_escape_demo()` — `glob.escape()` で特殊文字をエスケープ
- HTTP エンドポイント 5 本
- 27 テスト全通過（摩擦1件）

## テスト結果

初回: 1 失敗 → 修正後: 27 テスト全通過。

## Friction Points

### FP1: `fnmatchcase("Hello.py", "*.py")` は `True`（ワイルドカード部分は文字種に関係なくマッチ）

```python
fnmatch.fnmatchcase("Hello.py", "*.py")  # → True
```

`fnmatchcase` は大文字小文字を区別するが、ワイルドカード `*` はどんな文字列にもマッチする。
`Hello.py` に対して `*.py` を適用すると `*` が `Hello` にマッチし `.py` が `.py` にマッチするため `True` になる。

区別されるのはパターン内のリテラル文字部分のみ:

```python
fnmatch.fnmatchcase("Hello.py", "*.PY")   # → False (.PY と .py が不一致)
fnmatch.fnmatchcase("Hello.py", "hello.py")  # → False (Hello と hello が不一致)
fnmatch.fnmatchcase("Hello.py", "*.py")   # → True (* が Hello にマッチ、.py が .py にマッチ)
```

**対処**: テストの期待値を修正した。

## 観察

### O1: `fnmatch` のワイルドカード文字

| 文字 | 意味 |
|---|---|
| `*` | 任意の文字列（0文字以上） |
| `?` | 任意の1文字 |
| `[seq]` | seq 内の任意の1文字 |
| `[!seq]` | seq 外の任意の1文字 |

```python
fnmatch.fnmatch("file1.txt", "file?.txt")    # → True
fnmatch.fnmatch("file12.txt", "file?.txt")   # → False (? は1文字のみ)
fnmatch.fnmatch("file1.txt", "file[123].txt")  # → True
fnmatch.fnmatch("file4.txt", "file[123].txt")  # → False
```

### O2: Linux では `fnmatch.fnmatch` は大文字小文字を区別する

```python
# Linux: fnmatch は OS のファイルシステムに合わせる
fnmatch.fnmatch("Hello.py", "*.PY")  # → False (Linux: case-sensitive)
# Windows: True (Windows: case-insensitive)

# fnmatchcase は常に case-sensitive
fnmatch.fnmatchcase("Hello.py", "*.PY")  # → False (常に)
```

クロスプラットフォームで一貫した動作が必要なら `fnmatchcase` を使う。

### O3: `fnmatch.translate()` でパターンを正規表現に変換できる

```python
import re
pattern = fnmatch.translate("*.py")
# → '(?s:.*\\.py)\\Z' のような正規表現

re.match(pattern, "hello.py")  # → Match
re.match(pattern, "hello.js")  # → None
```

`re.compile()` でコンパイルすると繰り返しマッチが高速になる。

### O4: `glob.glob()` と `pathlib.Path.glob()` は同等の結果を返す

```python
# glob.glob: 文字列パスを使う
matched = glob.glob("/tmp/mydir/*.py")

# pathlib.Path.glob: Path オブジェクトを使う
matched = [p.name for p in Path("/tmp/mydir").glob("*.py")]
```

`pathlib.Path.glob()` はジェネレーターを返す（メモリ効率良し）。
`glob.iglob()` も同様に遅延評価のジェネレーターを返す。

### O5: `glob.escape()` でブラケット等の特殊文字をリテラルとして扱う

```python
filename = "[special].txt"
# このファイルを正確にマッチするには escape が必要
pattern = glob.escape(filename)  # → "\\[special\\].txt"
glob.glob(os.path.join(tmpdir, pattern))  # 正確にマッチ
```

ユーザー入力を glob パターンとして使う際は必ず `glob.escape()` を適用する。

### O6: `**` パターンは `pathlib.Path.glob()` の `recursive=True` 相当

```python
# すべてのサブディレクトリを再帰的に検索
list(Path(".").glob("**/*.py"))

# glob.glob でも recursive=True で同様
glob.glob("**/*.py", recursive=True)
```

## まとめ

FT159 は摩擦1件（`fnmatchcase` でワイルドカード部分は文字種に関係なくマッチする動作の誤解）。
`fnmatch` はファイル名パターンマッチのシンプルなAPIで、`glob` はファイルシステム上の
実ファイルにマッチする。`pathlib.Path.glob()` は `glob.glob()` のオブジェクト指向版で
モダンな Python では推奨される。
