# FT178: base64 モジュール

**日付**: 2026-05-21
**テーマ**: エンコード・デコード・URL セーフ変換・データ URI・HTTP Basic Auth パース
**セキュリティ診断**: なし（178 % 3 = 1）

---

## 概要

Web API で頻繁に使う `base64` モジュールを検証する。
標準エンコーディングと URL セーフ変換の違い、パディング扱い、データ URI 生成、
HTTP Basic Auth ヘッダーのパースまで網羅し、落とし穴となる箇所を洗い出す。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft178-base64/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `encode_standard(data)` | 標準 base64 エンコード（RFC 4648 §4） |
| `decode_standard(s)` | 標準 base64 デコード（`validate=True` で厳格検証） |
| `encode_url_safe(data)` | URL セーフ base64（パディングなし） |
| `decode_url_safe(s)` | URL セーフ base64 デコード（パディング自動補完 + 文字セット検証） |
| `encode_text(text)` | UTF-8 テキスト → base64 |
| `decode_text(s)` | base64 → UTF-8 テキスト（非 UTF-8 は `None`） |
| `is_valid_base64(s)` | 長さ・文字セット・パディングを検証 |
| `is_valid_url_safe_base64(s)` | URL セーフ文字セット検証 |
| `make_data_uri(content, mime_type)` | RFC 2397 データ URI 生成 |
| `parse_data_uri(uri)` | データ URI → `(mime_type, bytes)` |
| `encode_basic_auth(username, password)` | HTTP Basic Auth ヘッダー値生成 |
| `parse_basic_auth(header)` | Authorization ヘッダー → `(username, password)` |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/encode` | 標準 base64 エンコード |
| POST | `/decode` | 標準 base64 デコード |
| POST | `/encode/url-safe` | URL セーフ base64 エンコード |
| POST | `/decode/url-safe` | URL セーフ base64 デコード |
| POST | `/encode/text` | テキスト → base64 |
| POST | `/decode/text` | base64 → テキスト |
| POST | `/data-uri/encode` | データ URI 生成 |
| POST | `/data-uri/parse` | データ URI 解析 |
| POST | `/auth/basic/encode` | Basic Auth ヘッダー生成 |
| POST | `/auth/basic/parse` | Basic Auth ヘッダー解析 |

---

## テスト結果

**58 passed**（初回 1 失敗 → 修正後 58 全通過）

```
58 passed in 0.43s
```

mypy: Success / ruff: All checks passed / pip-audit: PYSEC-2025-183（継続監視）

---

## 摩擦ポイント

### F-1: `urlsafe_b64decode` が不正文字をサイレントに無視する（深刻度: 高）

**事象**: `decode_url_safe("!!!invalid!!!")` が `None` を返さず `b"\x8a{\xda\x96'"` を返した。

**原因**: `base64.urlsafe_b64decode()` は RFC 4648 の「ignore non-alphabet characters」モードで動作し、
`!` などの不正文字を黙って無視してデコードを続ける。
一方、標準の `b64decode(s, validate=True)` は不正文字で `binascii.Error` を raise する。

**対応**: `urlsafe_b64decode` の前に文字セット正規表現で事前バリデーション：
```python
_URL_SAFE_CHARS_RE = re.compile(r"^[A-Za-z0-9_\-=]*$")

def decode_url_safe(s: str) -> bytes | None:
    stripped = s.rstrip("=")
    if not stripped or not _URL_SAFE_CHARS_RE.match(stripped):
        return None
    ...
```

**ライブラリ設計上の問題**: `urlsafe_b64decode` に `validate=True` パラメータが存在しない（`b64decode` にはある）。
URL セーフ版は自前バリデーションが必要という非対称な API 設計。

---

## 観察点

### 観察1: 標準 base64 vs URL セーフ — `validate=True` の非対称性

```python
# 標準版: validate パラメータがある
base64.b64decode("not!!!valid", validate=True)  # → binascii.Error

# URL セーフ版: validate パラメータがない
base64.urlsafe_b64decode("not!!!valid")  # → サイレントに無視してデコード
```

JWT トークンや OAuth コードは URL セーフ base64 を使う。
`validate=True` に相当するガードを自前で実装しないと、
不正トークンを誤って「有効」として処理する脆弱性になりうる。

### 観察2: パディング補完の必要性

RFC 4648 §5 では URL セーフ base64 のパディング（`=`）は省略可能とされており、
JWT の `alg`・`typ` フィールドなど実際のトークンはパディングなしで渡ってくる。

```python
# パディングなし JWT ヘッダーを補完してデコード
stripped = s.rstrip("=")
padding = 4 - len(stripped) % 4
if padding != 4:
    s = stripped + "=" * padding
```

`padding != 4` の条件で「すでに 4 の倍数の場合はパディングを追加しない」ことも重要。

### 観察3: `partition(":")` で パスワード中のコロン対応

```python
username, _, password = text.partition(":")  # partition は最初の : で分割
```

`split(":", 1)` でも同じだが `partition` の方が意図が明示的で、
`a:b:c:d` → `("a", ":", "b:c:d")` の分解が 1 行で書ける。

### 観察4: データ URI の MIME タイプ検証

```python
re.match(r"^[a-zA-Z0-9][a-zA-Z0-9!#$&\-^_]*\/[a-zA-Z0-9][a-zA-Z0-9!#$&\-^_.+]*$", mime_type)
```

`image/png`・`application/octet-stream`・`text/plain; charset=utf-8` のような MIME タイプは正規表現で検証。
`javascript:`・`vbscript:` などの XSS ペイロードをデータ URI に埋め込む試みをブロックできる。

---

## nene2-python フレームワークとの統合

- `encode_basic_auth` / `parse_basic_auth` は `ApiKeyAuthMiddleware` の拡張として組み込み可能
- `make_data_uri` はファイルアップロード API のレスポンス形式として使える
- Pydantic `max_length` フィールドで全エンドポイントの DoS 対策済み
- `APIRouter` + `create_app()` パターン（FT177 摩擦 F-1 の対応）を最初から適用

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

画像アップロード API でクライアントから base64 エンコードされたデータを受け取る実装をしている。

**ドキュメント理解**: `b64encode` / `b64decode` のペアは分かりやすい。
URL セーフ版との違い（`+/` vs `-_`、パディング省略）はドキュメントに書いてないと気づきにくい。  
**事故リスク**: 中。標準版と URL セーフ版を混在させると復号に失敗し、バイナリ化けとして現れる。
エラーより「壊れたデータ」として扱われるため気づきにくい。  
**規約の使いやすさ**: `encode_standard(data)` が `str` を返し、`decode_standard(s)` が `bytes | None` を返すのは直感的。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

JWT パースのコードを既存プロジェクトからコピーしており、URL セーフ base64 を使っている。

**コピペ可能性**: `decode_url_safe` の自前バリデーションが必要な点はコメントがないと気づかない。
`urlsafe_b64decode` を直接使うと F-1 の罠にはまる。  
**拡張時の罠**: パディング補完のコードを「なんか動いてるから削ってもいいかな」と消すと壊れる。
なぜ必要かのコメントが欲しい。  
**セキュリティ的な事故リスク**: 高。JWT 検証で `urlsafe_b64decode` を `validate=True` なしで使うと、
改ざんトークンが「デコード成功」として扱われる可能性がある。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

TypeScript の `atob()` / `btoa()` に慣れており、Python で同じことをしようとしている。

**エラーレスポンスの質**: 400 Bad Request に具体的なメッセージ（"Invalid base64 input" 等）が返るのは良い。
クライアント側でデバッグしやすい。  
**Python 固有概念の学習コスト**: `bytes.hex()` / `bytes.fromhex()` の往復はTS では意識しない変換。
`atob()` は文字列を返すが `b64decode` は `bytes` を返す差異に戸惑う可能性。  
**事故リスク**: 低。HTTP 境界での Pydantic バリデーションが充実。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

JWT ライブラリの内部実装を理解しており、raw base64 操作をすることもある。

**他フレームワークとの差異**: Django の `base64.urlsafe_b64decode` 直接利用パターンと同じ罠（F-1）が
nene2-python でも起きる。フレームワーク側での救済ではなく実装者が知識として持つ必要がある。  
**nene2-python の薄さへの評価**: base64 は stdlib を薄くラップするだけが適切。
`decode_url_safe` のバリデーション付きラッパーは価値あるユーティリティ。  
**本番投入可能性**: Basic Auth のパースは `parse_basic_auth` 一本で安全に使える設計が好評価。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- [x] `urlsafe_b64decode` を自前バリデーションなしで使っていないか（F-1 の罠）
- [x] パスワードが base64 エンコードのみで「保護されている」と勘違いしていないか
  （base64 は暗号化ではなくエンコード）
- [x] Basic Auth をデコードして得たパスワードをそのまま平文比較していないか
  （`hmac.compare_digest` が必要）

**チームでの安全な共有パターン**: `decode_url_safe` に自前バリデーションを含めたラッパーを
ユーティリティとして共有すると、チーム全員が安全に使える。  
**ツール追加の必要性**: `ruff` に base64 固有のルールはなし。コードレビューで担保。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 中  
— F-1（`urlsafe_b64decode` の無バリデーション問題）は初心者が直接 `base64.urlsafe_b64decode` を使うと再発する。
`decode_url_safe` ラッパーを使う運用を周知する必要がある。  
**設計上の負債**: `validate=True` が URL セーフ版に存在しないのは Python stdlib の設計問題。
ユーザー向けに警告コメントを `decode_url_safe` に追記する価値がある。  
**Follow-up Issue 候補**: なし（現状の実装で十分）

---

## Follow-up Issues

今回の FT では実装上の重大な摩擦はなし（F-1 は実装内で解消済み）。

| 優先度 | タイトル | 種別 |
|---|---|---|
| 低 | `decode_url_safe` に「`urlsafe_b64decode` は validate=True がないため自前バリデーションが必要」コメントを追記 | docs |

---

## まとめ

FT178 では `base64` モジュールを中心に、Web API でよく使うエンコード操作を実装した。
58 テストが全通過し、mypy/ruff も問題なし。

最大の発見は F-1: `base64.urlsafe_b64decode` に `validate=True` がなくサイレントに不正入力を処理してしまう問題。
JWT・OAuth コード等を URL セーフ base64 で扱うコードが多い中、この挙動は高リスクな落とし穴。
文字セット正規表現による事前バリデーションで対応済み。

APIRouter パターン（FT177 F-1 からの改善）を最初から適用し、テストが一発で通過した。

v1.8.49 としてリリース。
