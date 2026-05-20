# Field Trial 136: re モジュールの高度な活用

## テーマ

名前付きグループ (`?P<name>`)、`finditer`、`re.MULTILINE`、`re.compile`、
lookahead (`(?=...)`) を使ったテキスト処理・バリデーション・パースを FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft136-regex/` に以下を実装:

- `EMAIL_PATTERN` — `(?P<local>...)@(?P<domain>...)\.(?P<tld>...)` で名前付きグループパース
- `PHONE_JP_PATTERN` — 日本の電話番号を `(?P<area>...)-?(?P<local>...)` でパース
- `LOG_PATTERN` — `re.MULTILINE` で複数行ログを `finditer` でスキャン
- `PASSWORD_CHECKS` — lookahead `(?=.*[A-Z])` 等で各条件を個別チェック
- `mask_sensitive()` — `re.sub` でメールアドレスとクレジットカード番号をマスク
- `extract_hashtags()` — `re.findall` でハッシュタグ抽出
- 22 テスト通過（摩擦1件あり：`re.MULTILINE` 忘れ + URL に改行不可）

## テスト結果

初回: 3失敗 → 修正後: 22テスト全通過。

## Friction Points

### FP1: `re.MULTILINE` を忘れると `^`, `$` が行頭・行末にマッチしない

```python
# NG: 複数行テキストで finditer してもマッチしない
LOG_PATTERN = re.compile(r"^(?P<timestamp>...)...")

# OK: re.MULTILINE で各行の先頭・末尾にマッチ
LOG_PATTERN = re.compile(r"^(?P<timestamp>...)...", re.MULTILINE)
```

デフォルトでは `^` は文字列全体の先頭、`$` は末尾のみにマッチする。
`re.MULTILINE` で `^` が各行の先頭、`$` が各行の末尾にマッチするようになる。

**対処**: 複数行テキストを行単位でパースする場合は `re.MULTILINE` を必ず付ける。

### FP2: クエリパラメーターに改行文字を含む URL は httpx が拒否する

```python
# テストで \n を含む text をクエリパラメーターとして渡そうとした
r = client.post(f"/parse/logs?text=line1\nline2")
# → httpx.InvalidURL: Invalid non-printable ASCII character in URL
```

URL には改行文字 (`\n`) を含めることができない。
ログテキストのように改行を含む入力は、クエリパラメーターではなくリクエストボディ（JSON）で渡す必要がある。

**対処**: 改行を含む可能性のある入力は Pydantic BodyModel で受け取る。

## 観察

### O1: 名前付きグループ `(?P<name>...)` で構造化データを取り出せる

```python
EMAIL_PATTERN = re.compile(
    r"^(?P<local>[a-zA-Z0-9._%+\-]+)@(?P<domain>[a-zA-Z0-9.\-]+)\.(?P<tld>[a-zA-Z]{2,})$"
)

match = EMAIL_PATTERN.match("user@example.com")
match.group("local")   # "user"
match.group("domain")  # "example"
match.group("tld")     # "com"
```

数値インデックス（`match.group(1)`）よりも名前付きグループが可読性が高い。

### O2: lookahead `(?=...)` でパスワードの各条件を独立してチェックできる

```python
PASSWORD_CHECKS = [
    (re.compile(r"(?=.*[A-Z])"), "uppercase"),
    (re.compile(r"(?=.*[a-z])"), "lowercase"),
]

results = {name: bool(pattern.search(password)) for pattern, name in PASSWORD_CHECKS}
```

lookahead は位置だけを確認して文字を消費しないため、
一つのパターンで複数条件をチェックするより、条件ごとに独立したパターンのほうが
メンテナンスしやすく、どの条件が失敗したかを個別に返せる。

### O3: `re.findall` でキャプチャグループのリストを返せる

```python
re.findall(r"#(\w+)", "Hello #world and #Python!")
# → ["world", "Python"]  (グループあり → グループの内容を返す)

re.findall(r"#\w+", "Hello #world and #Python!")
# → ["#world", "#Python"]  (グループなし → マッチ全体を返す)
```

## まとめ

FT136 は摩擦2件（`re.MULTILINE` の忘れ、改行文字をURLに含められない）。
どちらも一般的な落とし穴として記録する。名前付きグループと `re.MULTILINE` の
使い方をパターンとして確認した。
