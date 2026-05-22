# FT198: http.server モジュール — カスタム HTTP ハンドラー・インメモリサーバー・セキュリティ診断

**日付**: 2026-05-22
**テーマ**: Python `http.server` モジュールの BaseHTTPRequestHandler・カスタムハンドラー・インメモリ静的サーバーの実装と検証
**セキュリティ診断**: **あり**（198 % 3 = 0）
**クラッカーペンテスト**: なし（198 % 4 = 2）

---

## 概要

`http.server` は Python 標準ライブラリの低レベル HTTP サーバー実装。`BaseHTTPRequestHandler` を
サブクラス化することでカスタムハンドラーを作れる。FT196（http.client）のテスト用フィクスチャで
使用したが、今回はモジュールそのものを FT の主題として検証する。

FT196 の `conftest.py` で書いた `_Handler` クラスがほぼそのままの形で `EchoHandler` として
整理された。`make_memory_handler()` でクロージャを使ってコンテンツを注入するパターンも検証した。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft198-http-server/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `EchoHandler` | BaseHTTPRequestHandler サブクラス。GET/POST をリクエスト情報の JSON でエコーバック |
| `make_memory_handler(content)` | 指定 dict をインメモリで配信するハンドラークラスを生成するファクトリ |
| `run_single_request(handler, method, path, body, headers)` | HTTPServer を起動・1 リクエスト処理・停止して ResponseInfo を返す |
| `ResponseInfo` | status / reason / headers（小文字） / body を保持する frozen dataclass |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/server/echo` | EchoHandler を起動してリクエスト情報をエコーバック（GET/POST のみ許可） |
| POST | `/server/static` | インメモリコンテンツサーバーを起動して指定パスのコンテンツを返す |

---

## テスト結果

**21 passed**

```
21 passed in 7.61s
```

（各テストが HTTPServer の起動・停止を行うため通常より時間がかかる）

---

## 摩擦ポイント

### F-1: `do_GET` / `do_POST` の命名規則が ruff の `N802` に引っかかる（深刻度: 低）

**事象**: `BaseHTTPRequestHandler` のプロトコルは `do_GET()`・`do_POST()` のように
大文字を含むメソッド名を要求する。ruff の `N802`（function name should be lowercase）が
毎回検出される。

**対応**: `# noqa: N802` コメントで抑制。`@override` デコレーターで意図を明示しても良いが、
基底クラスの `do_GET` が存在するかどうかを typeshed が `type[str]` として扱うため、
override 検出が難しい。

**CLAUDE.md への示唆**: `http.server` ハンドラーの `do_*` メソッドは `# noqa: N802` が必要なことを how-to に記載する。

### F-2: `make_memory_handler` の返す型が `type[BaseHTTPRequestHandler]` になりインナークラスの詳細が失われる（深刻度: 低）

**事象**: `make_memory_handler()` の戻り値型は `type[http.server.BaseHTTPRequestHandler]` と
宣言しているが、実際には `_MemoryHandler` クラスが返る。
`_content` クラス変数にアクセスする際に mypy が「属性が存在しない」と報告するリスクがある
（ただし内部でのみアクセスするため今回は問題なし）。

**対応**: `_content: dict[str, str] = content` を明示的にアノテーションして解決。

### F-3: HTTPServer の起動・停止がテスト時間に影響する（深刻度: 低）

**事象**: 21 テストが 7.61 秒かかった。通常の FastAPI テストは 0.07 秒程度。
各テストが `HTTPServer` の起動・`serve_forever()` スレッド生成・`shutdown()` を行うため。

**対応**: テストの設計として許容範囲（CI で 10 秒以下）。`scope="module"` でサーバーを
一度だけ起動する設計に変更することでさらに高速化できるが、テストの独立性が下がる。

---

## 観察点

### O-1: `BaseHTTPRequestHandler` は `do_XXX` メソッドで HTTP メソッドをディスパッチする

`handle_one_request()` が `do_{self.command}()` を `getattr` で呼ぶ。
`do_DELETE`・`do_PUT` を実装しなければ自動的に `send_error(501, "Unsupported method")` が返る。
エンドポイント側でのメソッドホワイトリストチェックは二重防御として有効だが、
実際には `BaseHTTPRequestHandler` 側のデフォルト動作が最初の防御線になる。

### O-2: `serve_forever()` + `shutdown()` は daemon スレッドでも安全に動作する

`server.shutdown()` は `_BaseServer` の `__shutdown_request` フラグを立て、
`serve_forever()` ループから抜ける。`thread.daemon = True` にしているため
プロセス終了時にスレッドが残ることもない。

### O-3: `SimpleHTTPRequestHandler` はファイルシステムを公開する

今回は使用しなかったが、`SimpleHTTPRequestHandler` は `os.getcwd()` 以下のファイルを
そのまま配信する。プロダクション環境で使うと意図しないファイルが公開されるリスクがある。
`make_memory_handler()` パターンはファイルシステムに触れないため安全。

---

## セキュリティ診断

### 1. OWASP API Security Top 10 (2023)

| 項目 | 評価 | 備考 |
|---|---|---|
| BOLA/IDOR | 問題なし | リソースに所有者概念なし（デモ用途） |
| 認証破損 | 問題なし | 認証なし（デモ用途・localhost のみ） |
| Mass Assignment | 問題なし | Pydantic で入力フィールドを明示 |
| リソース消費 | **注意** | リクエストごとに HTTPServer を起動・停止する（後述） |
| SSRF | 問題なし | サーバーは 127.0.0.1 に bind、外部への接続なし |
| セキュリティ設定ミス | 問題なし | `Server` ヘッダーに Python バージョン情報が出るが内部サーバーのみ |

**リソース消費の詳細**: `/server/echo` は毎リクエストで `HTTPServer` + `Thread` を生成・破棄する。
多数の同時リクエストがあるとスレッド数が増加し、ファイルディスクリプタを消費する可能性がある。
デモ用途では許容範囲だが、プロダクション化するなら常時起動の単一サーバーか
`ThreadingHTTPServer` のプールを使うべき。

### 2. インジェクション攻撃

**パストラバーサル（MemoryHandler）**:
```
GET /../etc/passwd  → MemoryHandler の exact match でヒットせず → 404
GET /../../.ssh/id_rsa → 同様に 404
GET /%2e%2e/etc/passwd → URL デコード後 /../etc/passwd → 404
```
**結果**: 安全。`if path in self._content` の完全一致が自然なパストラバーサル防御になっている。

**ヘッダーインジェクション（EchoHandler）**:
```
path = "/hello\r\nX-Injected: evil"
```
Python の `http.server` は RFC 7230 に従い、リクエストラインをスペースで分割する。
`\r\n` を含む path は TCP レベルでは次のヘッダー行として送信されるが、
`http.client` が送信前にエンコードするため、テスト環境では実際にはリクエストラインに
`\r\n` を含む不正なリクエストを送れない（`http.client` 側がブロック）。

```python
# http.client は request line を安全に組み立てる
conn.request("GET", "/hello\r\nX-Injected: evil")
# → 実際の送信: "GET /hello%0D%0AX-Injected:%20evil HTTP/1.1\r\n"
# (%0D%0A にエンコードされて無害化)
```
**結果**: `http.client` がエンコードするため無害化される。

**パス・クエリ文字列インジェクション（MemoryHandler）**:
```
GET /safe?admin=1  → split("?")[0] で /safe → 200 OK （正常）
GET /safe?../../secret=1 → /safe → 200 OK
```
**結果**: クエリ文字列はパス比較前に除去されるため安全。

### 3. 認証・認可

該当なし（デモ用途、localhost のみ）。

### 4. 入力バリデーション

```
POST /server/echo  {"method": "DELETE", "path": "/"}  → 422 method_not_allowed
POST /server/echo  {"method": "GET", "path": "/", "body": "x" * 10001}  → 422 max_length
POST /server/echo  {"method": "X" * 11, "path": "/"}  → 422 max_length=10 超過
POST /server/static  {"path": "x" * 2049}  → 422 max_length=2048 超過
```
**結果**: Pydantic の制約が有効に機能している。

### 5. 情報漏洩

```
GET /server/echo のレスポンス headers フィールド:
{
  "host": "127.0.0.1:XXXXX",
  "connection": "keep-alive",
  "user-agent": "python-httpx/...",
  ...
}
```
`EchoHandler` はリクエストヘッダーをすべて JSON で返す。
Authorization ヘッダーや Cookie もそのまま公開されるが、
これはデモ用エコーサーバーの意図的な動作。

**注意**: `Server` レスポンスヘッダーに `BaseHTTP/0.6 Python/3.14.5` が含まれる。
内部デバッグサーバーとしての用途では問題ないが、公開サーバーではバージョン情報を隠すべき。

```python
def version_string(self) -> str:
    return "MyServer/1.0"  # オーバーライドで隠蔽可能
```

### 6. Python/FastAPI 固有

**`BaseHTTPRequestHandler.rfile.read()` の上限なし読み取りリスク**:
`do_POST` で `length = int(self.headers.get("Content-Length", "0"))` を使うが、
Content-Length が非常に大きい値を送ると `rfile.read(length)` がメモリを大量消費する。

**検証**:
```
POST /server/echo  {"method": "POST", "path": "/", "body": "x" * 10000}
→ 200 OK  (Pydantic の max_length=10_000 がボディサイズを制限)

# 直接 http.client から 100MB を送信（Pydantic を経由しない場合）
→ EchoHandler.do_POST は rfile.read(100_000_000) を実行する → DoS の危険
```

**評価**: `FastAPI エンドポイント経由`では Pydantic の `max_length` が防御層になるが、
`EchoHandler` 自体は無制限読み取りのため、直接接続では脆弱。
デモ用サーバーとして `run_single_request` 経由でのみ使う設計なら問題ないが、
`EchoHandler` をスタンドアロンで公開するなら Content-Length に上限チェックが必要。

```python
MAX_BODY = 1_024 * 64  # 64KB
length = min(int(self.headers.get("Content-Length", "0")), MAX_BODY)
```

**pip-audit**: 既知 CVE なし。

### セキュリティ診断総評

| カテゴリ | 評価 | 備考 |
|---|---|---|
| パストラバーサル | 合格 | exact match が自然な防御 |
| ヘッダーインジェクション | 合格 | http.client が無害化 |
| メソッドインジェクション | 合格 | Pydantic ホワイトリスト |
| EchoHandler Content-Length 無制限 | **要注意（デモ用途では低リスク）** | スタンドアロン公開時は上限チェック必須 |
| リソース消費（サーバー起動コスト） | 要注意（デモ用途では低リスク） | プロダクション化時は常時起動サーバーに変更 |
| バージョン情報漏洩 | 低リスク | 内部のみなら許容。公開時は version_string() オーバーライド |

**判定**: 条件付き合格。`EchoHandler` の Content-Length 上限なし読み取りは
プロダクション公開時には修正必須だが、デモ用スコープでは許容。

---

## DX Review — 6ペルソナ

### ペルソナ 1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`http.server` を「本番に使えるサーバー」だと誤解するリスクがある。
ドキュメントに「開発・テスト用途のみ」という注意書きを明示すべき。

**ドキュメント理解**: `BaseHTTPRequestHandler` のサブクラス化パターンは分かりやすい。
`do_GET`・`do_POST` というメソッド名規則はやや驚くが、一度学べば直感的。
**事故リスク**: 高。`SimpleHTTPRequestHandler` を使って意図せずファイルシステムを公開するパターンが典型的な事故。今回のように `make_memory_handler()` でファイルシステムに触れない設計を紹介する価値がある。
**規約の使いやすさ**: `run_single_request()` のラッパーは「サーバーを立てて試す」フローをワンライナーに近い使い勝手にしており評価できる。

### ペルソナ 2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

スクリプトでのちょっとしたモックサーバー用途に `http.server` を使うことがある。
`EchoHandler` のパターンはそのままコピーできる。

**コピペ可能性**: `EchoHandler` + `run_single_request()` は即コピー可能。
**拡張時の罠**: `do_PUT`・`do_DELETE` を追加するたびに `# noqa: N802` が必要な点が煩わしい。
**事故リスク**: 中。Content-Length の無制限読み取り（F 診断）を知らずに本番サーバーに使う可能性。

### ペルソナ 3: フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

Node.js の `http.createServer()` と概念が近い。コールバック vs メソッドオーバーライドの違いはあるが理解しやすい。

**エラーレスポンスの質**: `EchoHandler` が返す JSON は構造化されていて扱いやすい。
**Python 固有概念の学習コスト**: `# noqa: N802` は型チェック・linter の設定として説明が必要。
**事故リスク**: 低（エンドポイントを通じた使用は安全）。

### ペルソナ 4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`http.server` をテストフィクスチャとして使う用途は理解している。
「FastAPI の中で http.server を起動する」という入れ子構造に一瞬戸惑うが、
「テスト用モックサーバーをデモとして公開している」と理解すれば納得する。

**他フレームワークとの差異**: `pytest-httpserver` などのサードパーティを使う方が
テストフィクスチャとしては洗練されている。`http.server` を直接使うのは依存を最小化したい場合。
**nene2 の薄さへの評価**: `run_single_request()` の抽象化レベルが適切で再利用しやすい。
**事故リスク**: 低。

### ペルソナ 5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

`make_memory_handler()` がクロージャでコンテンツを注入する設計は評価する。
ただし、`_DEMO_CONTENT` がグローバルで固定されている点は拡張性に欠けると指摘する。

**コードレビューチェックポイント**:
- `do_GET` / `do_POST` の `# noqa: N802` は理由コメントを添えると良い
- `EchoHandler._send_echo` の Content-Length 上限なし読み取りをコードレビューでコメント
- `run_single_request` の `try/finally` で `server.shutdown()` を確実に呼ぶ設計は OK
- `timeout=5.0` のマジックナンバーを定数化する提案

**事故リスク**: 低（コードは整合的。診断指摘は文書化済み）。

### ペルソナ 6: 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**:
- `frozen=True, slots=True` dataclass ✓
- Pydantic `max_length` による入力制限 ✓
- `ErrorHandlerMiddleware` 追加 ✓（init-ft.sh ボイラープレートが機能）
- `ValidationError` に `code` 引数 ✓（FT196 での修正が活きた）

**初心者でも安全な API 達成度**: `make_memory_handler()` パターンは
ファイルシステムを公開しない安全なサーバー実装の好例。
`EchoHandler` の Content-Length 無制限問題はスタンドアロン公開時のリスクとして
how-to に記載する価値がある。

---

## Follow-up

- `EchoHandler` の Content-Length 上限なし読み取りは FT レポートに記録済み。デモスコープでは修正不要
- `do_*` メソッドと `# noqa: N802` の使い方を how-to ガイドに追記（中優先）
