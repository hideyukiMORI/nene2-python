# Field Trial 149: csv モジュール

## テーマ

`csv.reader`, `csv.writer`, `csv.DictReader`, `csv.DictWriter`, `csv.Sniffer`
を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft149-csv/` に以下を実装:

- `parse_csv()` — `csv.reader` で CSV テキストを 2D リストに変換
- `parse_csv_dict()` — `csv.DictReader` でヘッダー付き辞書リストに変換
- `write_csv()` — `csv.writer` で 2D リストを CSV テキストに変換
- `write_csv_dict()` — `csv.DictWriter` で辞書リストを CSV テキストに変換
- `detect_dialect()` — `csv.Sniffer.sniff()` でデリミタ・引用符を自動検出
- `has_header()` — `csv.Sniffer.has_header()` でヘッダー行を検出
- `csv_to_json()` / `json_to_csv()` — 変換ユーティリティ
- HTTP エンドポイント 6 本
- 25 テスト全通過（摩擦0件）

## テスト結果

初回: 25 テスト全通過。摩擦なし。

## 摩擦なし

今回はブロッカーとなる摩擦なし。`io.StringIO` を使うことで
ファイル I/O なしに CSV 処理を実現できた。

## 観察

### O1: `io.StringIO` でインメモリ CSV 処理ができる

```python
def parse_csv(text: str) -> list[list[str]]:
    reader = csv.reader(io.StringIO(text))
    return [row for row in reader if row]

def write_csv(rows: list[list[str]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    return output.getvalue()
```

`csv.reader` / `csv.writer` はファイルオブジェクトを受け取るが、
`io.StringIO` でインメモリ文字列を渡せるためファイルなしで CSV 処理できる。

### O2: `csv.DictReader` はヘッダー行を自動的にキーに使う

```python
reader = csv.DictReader(io.StringIO(text))
records = [dict(row) for row in reader]
# 先頭行が {"name": "Alice", "age": "30", "city": "Tokyo"} のキー名になる
```

`fieldnames` 引数を省略すると最初の行がヘッダーとして扱われる。
`dict(row)` で変換するのは `DictReader` が `OrderedDict` (py3.8 以降は通常 `dict`) を返すが
型注釈を明確にするため。

### O3: `csv.DictWriter` は fieldnames でカラム順序と選択を制御する

```python
writer = csv.DictWriter(output, fieldnames=["name", "age"])
writer.writeheader()
writer.writerows(rows)
```

`extrasaction="ignore"` を指定すると `fieldnames` にないキーを無視できる。
デフォルトは `"raise"` で余分なキーがあると `ValueError` を送出する。

### O4: `csv.Sniffer` でデリミタを自動検出できる

```python
sniffer = csv.Sniffer()
dialect = sniffer.sniff(text[:1024])
print(dialect.delimiter)  # "," または "\t" など
print(sniffer.has_header(text[:1024]))  # True/False
```

`sniff()` はサンプルテキスト（先頭 1024 バイト程度で十分）を解析して
`csv.Dialect` サブクラスを返す。
`has_header()` はヘッダー行の有無を統計的に判定する。

### O5: CSV の引用符とエスケープは自動処理される

```python
rows = [["name", "bio"], ['Alice', 'loves "Python"']]
text = write_csv(rows)
# → name,bio\r\n"Alice","loves ""Python"""\r\n
parsed = parse_csv(text)
assert parsed[1][1] == 'loves "Python"'  # ✅ ダブルクォートが復元される
```

`csv.writer` は引用符を含むフィールドを自動的にダブルクォートで囲み、
内部の引用符をダブルクォート (`""`) でエスケープする。

### O6: 改行を含むフィールドを正しく扱う

```python
CSV_QUOTED = 'name,bio\n"Alice","line1\nline2"'
rows = parse_csv(CSV_QUOTED)
assert "\n" in rows[1][1]  # ✅ フィールド内の改行が保持される
```

`csv.reader` は引用符で囲まれたフィールド内の改行をフィールドの一部として扱う。

### O7: TSV はデリミタを変えるだけで対応できる

```python
rows = parse_csv(text, delimiter="\t")
text = write_csv(rows, delimiter="\t")
```

`delimiter` パラメータで CSV・TSV・その他の区切り文字に対応できる。

## まとめ

FT149 は摩擦ゼロ。`csv` モジュールは `io.StringIO` と組み合わせることで
ファイルなしのインメモリ処理が簡単にでき、引用符・エスケープ・改行を含む
フィールドも自動的に正しく処理される。`csv.Sniffer` はデリミタ自動検出に
便利だが、サンプルサイズを適切に制限する必要がある。
