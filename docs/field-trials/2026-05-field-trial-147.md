# Field Trial 147: urllib.parse モジュール

## テーマ

`urllib.parse.urlparse`, `urlunparse`, `urlencode`, `urljoin`,
`quote`, `unquote`, `parse_qs`, `parse_qsl` を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft147-urllib-parse/` に以下を実装:

- `parse_url()` — URL を scheme/host/path/query/fragment 等に分解
- `build_url()` — `urlunparse` でコンポーネントから URL を組み立て
- `parse_query_string()` — `parse_qs` で同名パラメーターをリストにまとめる
- `parse_query_ordered()` — `parse_qsl` で順序保持パース
- `build_query_string()` — `urlencode` でクエリ文字列を生成
- `encode_component()` — `quote(text, safe="")` で全文字をエンコード
- `encode_path_segment()` — `quote(text, safe="/")` でスラッシュを保持
- `decode_component()` — `unquote` でデコード
- `resolve_url()` — `urljoin` で相対 URL を解決
- 29 テスト通過（摩擦1件あり）

## テスト結果

初回: 1失敗 → 修正後: 29テスト全通過。

## Friction Points

### FP1: `urllib.parse.quote()` のデフォルト `safe` はスラッシュを含む

```python
from urllib.parse import quote

# デフォルト: safe="/" — スラッシュはエンコードしない
quote("path/segment")  # → "path/segment" (スラッシュが残る!)

# スラッシュも含めてエンコードする場合は safe="" が必要
quote("path/segment", safe="")  # → "path%2Fsegment"

# パスセグメント（スラッシュ保持）
quote("path/segment", safe="/")  # → "path/segment"
```

URL コンポーネント全体をエンコードする意図で `quote(text)` を使ったが、
デフォルトの `safe="/"` がスラッシュをエンコードしなかった。
クエリパラメーター値やパスの一部をエンコードする場合は `safe=""` が必要。

**対処**: `encode_component()` を `quote(text, safe="")` に修正した。

## 観察

### O1: `urlparse` で URL を 6 コンポーネントに分解できる

```python
result = urlparse("https://user:pass@example.com:8080/path?q=1#section")
result.scheme    # "https"
result.netloc    # "user:pass@example.com:8080"
result.path      # "/path"
result.query     # "q=1"
result.fragment  # "section"
result.hostname  # "example.com"
result.port      # 8080 (int)
result.username  # "user"
result.password  # "pass"
```

`netloc` は `username:password@hostname:port` の複合フィールド。
`hostname`, `port`, `username`, `password` は個別プロパティで取得できる。

### O2: `parse_qs` は同名パラメーターをリストにまとめる

```python
parse_qs("tag=python&tag=fastapi")  # → {"tag": ["python", "fastapi"]}
parse_qsl("tag=python&tag=fastapi") # → [("tag", "python"), ("tag", "fastapi")]
```

`parse_qs` は値を常にリストで返す（単一値も `["value"]`）。
`parse_qsl` は順序を保持したタプルリストで返す。

### O3: `urljoin` は相対 URL の解決に使う

```python
urljoin("https://example.com/foo/bar", "baz")    # → "https://example.com/foo/baz"
urljoin("https://example.com/foo/bar", "/baz")   # → "https://example.com/baz"
urljoin("https://example.com/foo/bar", "?q=1")   # → "https://example.com/foo/bar?q=1"
urljoin("https://example.com/foo/", "baz")       # → "https://example.com/foo/baz"
```

末尾スラッシュの有無でベースパスの解釈が変わる点に注意。

### O4: `urlencode` はスペースを `+` でエンコードする（`%20` ではない）

```python
urlencode({"q": "hello world"})  # → "q=hello+world"
```

HTML フォームの `application/x-www-form-urlencoded` 形式（RFC 1866）では
スペースは `+` で表現する。URL パス内では `%20` が正しい。
パス内エンコードには `quote(text, safe="")` を使う。

## まとめ

FT147 は摩擦1件（`quote()` のデフォルト `safe="/"` によるスラッシュの残存）。
URL 解析・クエリパラメーター操作・パーセントエンコーディングを FastAPI で確認した。
