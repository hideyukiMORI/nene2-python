# Field Trial 140: io モジュール + バイナリ処理

## テーマ

`BytesIO`, `StringIO`, `base64`, `hashlib`, CSV/JSON の in-memory 処理を
FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft140-io-binary/` に以下を実装:

- `encode_base64()` / `decode_base64()` — `base64.b64encode/b64decode`
- `compute_hash()` — `hashlib.new(algorithm)` でハッシュ計算
- `process_binary_chunks()` — `io.BytesIO` でチャンク分割
- `csv_to_json()` / `json_to_csv()` — `io.StringIO` で CSV ↔ JSON 変換
- `pretty_print_json()` — `io.StringIO` に `json.dump` で整形 JSON
- Base64/Hash/CSV変換の HTTP エンドポイント
- 22 テスト通過（摩擦1件あり）

## テスト結果

初回: 1失敗 → 修正後: 22テスト全通過。

## Friction Points

### FP1: クエリパラメーターに改行文字を含む URL は httpx が拒否する（FT136 と同様）

CSV テキストをクエリパラメーターとして渡したが、改行文字 (`\n`) を含む URL を
httpx が `InvalidURL` として拒否した（FT136 でも同じ問題が発生済み）。

**対処**: 改行を含む可能性のある入力は常に Pydantic BaseModel ボディとして受け取る。
これは再発パターン — CLAUDE.md に「改行を含む入力はボディ経由」と明記すべき候補。

## 観察

### O1: `io.BytesIO` でバイナリデータをファイルのように読み書きできる

```python
buffer = io.BytesIO(data)
chunk = buffer.read(chunk_size)  # N バイト読み取り
buffer.seek(0)                   # 先頭に戻る
buffer.write(b"more data")       # 追記
```

`BytesIO` はバイナリデータをメモリ内でファイルとして扱えるため、
`read(n)` などファイル API と同じインターフェースで処理できる。

### O2: `io.StringIO` で CSV・JSON の in-memory 処理ができる

```python
# CSV → dict
reader = csv.DictReader(io.StringIO(csv_text))
records = [dict(row) for row in reader]

# dict → CSV
output = io.StringIO()
writer = csv.DictWriter(output, fieldnames=records[0].keys())
writer.writeheader()
writer.writerows(records)
csv_text = output.getvalue()
```

一時ファイルを使わずにメモリ内で CSV を読み書きできる。

### O3: `hashlib.new(algorithm)` でアルゴリズムを文字列で動的に指定できる

```python
hasher = hashlib.new("sha256")
hasher.update(data)
digest = hasher.hexdigest()
```

`hashlib.sha256(data).hexdigest()` より `hashlib.new(algo)` の方が
動的なアルゴリズム選択に柔軟。未知アルゴリズムは `ValueError` を raise する。

### O4: `json.dump(..., ensure_ascii=False)` で日本語を非エスケープで出力できる

```python
json.dump({"message": "こんにちは"}, output, ensure_ascii=False)
# → {"message": "こんにちは"} (ASCII エスケープなし)

json.dump({"message": "こんにちは"}, output)
# → {"message": "こんにちは"} (デフォルト)
```

## まとめ

FT140 は摩擦1件（クエリパラメーターへの改行含む入力 — FT136 と同様の既知パターン）。
`BytesIO`/`StringIO` による in-memory 処理を FastAPI エンドポイントで確認した。
CSV/JSON 変換のラウンドトリップも正確に動作することを確認した。
