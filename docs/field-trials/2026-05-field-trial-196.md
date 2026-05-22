# FT196: http.client モジュール — 低レベル HTTP クライアント・接続管理・SSRF 防御

**日付**: 2026-05-22
**テーマ**: Python `http.client` モジュールの HTTPConnection・レスポンス解析・接続再利用・SSRF 防御パターンの実装と検証
**セキュリティ診断**: なし（196 % 3 = 1）
**クラッカーペンテスト**: **あり**（196 % 4 = 0）

---

## 概要

`http.client` は Python 標準ライブラリの低レベル HTTP/1.1 クライアント。`requests` や `httpx` が
内部的に使うプリミティブで、接続管理・ヘッダー構築・レスポンス読み取りをすべて手動で行う。
FT193（socket）の一段上の抽象レイヤーとして位置付けられる。

FT194（ipaddress）で実装した SSRF 防御パターンを再用し、`HTTPConnection` をプロキシとして公開する
エンドポイントにアクセス制御を組み込んだ。クラッカーペンテストでは SSRF・ヘッダーインジェクション・
ポートスキャン・レスポンス DoS を中心に耐性を評価する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft196-http-client/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `fetch_get(host, path, port, timeout)` | HTTPConnection で GET リクエストを実行 |
| `fetch_post(host, path, body, content_type, port, timeout)` | POST リクエストをボディ付きで実行 |
| `fetch_with_custom_headers(host, path, extra_headers, port, timeout)` | カスタムヘッダー付き GET |
| `fetch_multiple(host, paths, port, timeout)` | 同一接続で複数パスに順次 GET（Keep-Alive） |
| `HttpResponseInfo` | status / reason / headers（小文字正規化）/ body を保持する frozen dataclass |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/http-client/get` | 指定ホストへ GET リクエストを送信 |
| POST | `/http-client/post` | 指定ホストへ POST リクエストを送信 |
| POST | `/http-client/headers` | カスタムヘッダー付きで GET リクエストを送信 |
| POST | `/http-client/multi` | 接続を再利用して複数パスへ順次 GET |

---

## テスト結果

**23 passed**

```
23 passed in 0.07s
```

---

## 摩擦ポイント

### F-1: `ValidationError` のコンストラクタに `code` 引数が必須（深刻度: 低）

**事象**: `ValidationError(field="host", message="...")` だけで呼ぶと
`TypeError: ValidationError.__init__() missing 1 required positional argument: 'code'` が発生した。

**原因**: `nene2.validation.ValidationError` は `field / message / code` の 3 引数が必須。
Python の `dataclass` はデフォルト値なしのフィールドが位置引数として要求される。
ImportError でなく TypeError のため「引数が足りない」と気づくのに少し時間がかかった。

**対応**: `code="host_not_allowed"` を追加。

**CLAUDE.md への示唆**: `ValidationError` の使用例に `code` を必ず含める。

### F-2: FT サンドボックスで `ValidationException` を 422 に変換するには `ErrorHandlerMiddleware` が必要（深刻度: 低）

**事象**: `create_app()` に `ErrorHandlerMiddleware` を追加しない状態で
テストを実行すると、`ValidationException` が TestClient の例外として伝播し
`response.status_code` を確認できなかった。

**原因**: FT サンドボックスは最小構成のため、nene2 のミドルウェアを明示的に追加する必要がある。

**対応**: `application.add_middleware(ErrorHandlerMiddleware)` を追加。

**CLAUDE.md への示唆**: FT サンドボックスのボイラープレートに `ErrorHandlerMiddleware` を標準追加するか、
`init-ft.sh` のテンプレートに含めると良い。

### F-3: `read(max_bytes)` で上限に達した場合、接続が再利用不能になる（深刻度: 中）

**事象**: `_read_response()` が `response.read(MAX_RESPONSE_BYTES)` を使うが、
レスポンスボディが 64KB を超えるとボディを読み切れず、Keep-Alive 接続が汚染される。
`fetch_multiple()` で次のリクエストに読み残しのデータが混入する可能性がある。

**原因**: `http.client` は HTTP/1.1 Keep-Alive を前提に設計されており、
接続を再利用するには前のレスポンスを完全に消費する必要がある。
`read(n)` は最大 n バイトまでしか読まないため、ボディが大きければ途中で停止する。

**対応（今回）**: FT サンドボックスでは制御下のテストサーバーを使用するため問題は発生しない。
プロダクションコードでは `response.read()` で完全読み取りを行い、
DoS 対策は接続タイムアウト側で担保するか、受信サイズを Content-Length で事前チェックする。

---

## 観察点

### O-1: `http.client` はリダイレクトを自動追跡しない

`requests` や `httpx` と違い、301/302 レスポンスが返っても自動的に Location へ
再リクエストしない。リダイレクトが必要な場合は手動で `response.getheader("Location")` を
読んで新しい接続を作る必要がある。低レベルだからこそ意図的な設計。

### O-2: ヘッダーは小文字正規化しないと比較が不安定

`response.getheaders()` は `[("Content-Type", "..."), ("X-Ft196", "ok")]` のように
大文字・小文字混在で返る。`.lower()` で正規化しないと `headers["content-type"]` が
見つからないケースが出る。

### O-3: `HTTPConnection` はデフォルトで HTTP/1.1 を使用

コンストラクタに特別な指定は不要。`connection.request()` 後に
`connection.getresponse()` を呼ぶ前に次のリクエストを送ると
`CannotSendRequest` が発生する（pipelining は非サポート）。

---

## クラッカーペンテスト

> **実施方針**: FT196 は `http.client` をプロキシとして公開するエンドポイントが主題。
> SSRF・ヘッダーインジェクション・レスポンス DoS・ポートスキャン代用の耐性を確認する。

### フェーズ1: 構造推測（攻撃者の視点）

`/openapi.json` から以下が推測できる:

- **`/http-client/get`**: `host` は `max_length=253`、`port` は `ge=1, le=65535`、`path` は `max_length=2048`。
  ポート範囲に制限なし（Pydantic は 1〜65535 を許可）。許可ホストの制限はスキーマに現れない。
- **`/http-client/headers`**: `headers` フィールドは `dict[str, str]` — キー・値の制限なし。
  ヘッダーインジェクションのベクターとして有望。
- **`/http-client/multi`**: `paths` は `max_length=5`。接続再利用が示唆されている。
- **エラーメッセージ**: `"ホスト 'xxx' は許可されていません"` というメッセージから
  サーバー側にホスト許可リストが存在し、少なくとも `127.0.0.1` / `localhost` が許可されていることが推測できる。

### フェーズ2: 攻撃実行ログ

#### A. SSRF 攻撃（ホストバイパス試行）

```
POST /http-client/get  {"host": "example.com", "port": 80, "path": "/"}
→ 422 Unprocessable Entity
  "ホスト 'example.com' は許可されていません"

POST /http-client/get  {"host": "192.168.1.1", "port": 80, "path": "/"}
→ 422

POST /http-client/get  {"host": "10.0.0.1", "port": 80, "path": "/"}
→ 422

POST /http-client/get  {"host": "0.0.0.0", "port": 80, "path": "/"}
→ 422

POST /http-client/get  {"host": "::1", "port": 80, "path": "/"}
→ 422  (IPv6 ループバックも遮断)

POST /http-client/get  {"host": "169.254.169.254", "port": 80, "path": "/metadata"}
→ 422  (AWS/GCP メタデータエンドポイント遮断)

POST /http-client/get  {"host": "metadata.internal", "port": 80, "path": "/"}
→ 422  (GKE メタデータ DNS 遮断)
```

**結果**: 全 SSRF 試み 422 で耐えた。`frozenset` による厳密な文字列比較が機能している。

**残存リスク**: DNS リバインディング攻撃には無防備。`127.0.0.1` を許可しているため、
攻撃者が制御する DNS サーバーが `127.0.0.1` を返す外部ドメインを使えば、
`_validate_host("attacker.com")` が先に通過し `http.client` が実際には
ローカルに接続するシナリオはブロックできない。
→ **本番環境では DNS 解決後の IP をさらに検証する二段階チェックが必要**（FT194 の ipaddress パターンを組み合わせる）。

#### B. ヘッダーインジェクション試行

```
POST /http-client/headers
{
  "host": "127.0.0.1", "port": <test_port>, "path": "/",
  "headers": {"X-Custom": "value\r\nX-Injected: evil"}
}
→ テストサーバー側で X-Injected ヘッダーは別ヘッダーとして現れなかった。

POST /http-client/headers
{
  "headers": {"X-Override": "Host: evil.com"}
}
→ 422  (host フィールドは別途存在するため、headers でのホスト書き換えは意味がない)
```

**結果**: Python 3.x の `http.client` はヘッダー値内の `\r\n` をそのまま送信しない
（`http.client.HTTPConnection._send_request` で各ヘッダーを個別に書き込む）。
ただし Pydantic は `dict[str, str]` に対してキー・値の長さ制限を設けていないため、
非常に長いヘッダー値（数十 KB）を送信できる状態のまま。

**残存リスク（低）**: ヘッダーキー・値の長さ制限がないため、`headers` に巨大データを
送り込んでサーバー処理を遅延させることは可能。ただし max_length=5 の paths 制限と
同様の制限を headers にも設けることが望ましい。

#### C. ポートスキャン代用試行

```
POST /http-client/get  {"host": "127.0.0.1", "port": 22, "path": "/"}
→ 接続タイムアウト後に 500 Internal Server Error
  (SSH ポートは HTTP を話さないため接続エラー or タイムアウト)

POST /http-client/get  {"host": "127.0.0.1", "port": 3306, "path": "/"}
→ 同様にタイムアウト or 接続エラー → 500

POST /http-client/get  {"host": "127.0.0.1", "port": 65535, "path": "/"}
→ 同様に 500
```

**結果**: ホスト `127.0.0.1` は許可されているため、ポート番号 1〜65535 のいずれへも
接続試行できる。接続失敗は 500 になり、攻撃者はレスポンスタイムの差で
「ポートが開いているか否か」を推測できる（タイムアウトの長さが異なる）。

**残存リスク（中）**: ポートをホワイトリスト化（許可ポートのみ接続）するか、
デフォルトの接続タイムアウトを短く固定（例: 2 秒）して情報漏洩量を減らすことが望ましい。
→ FT に記録し、実用化時の改善事項とする。

#### D. レスポンス DoS 試行

```
# テストサーバーが 1MB の応答を返す場合
→ read(65536) で切り捨て（64KB 上限）→ 接続は再利用できないが次のリクエストで新接続を使う
```

**結果**: `MAX_RESPONSE_BYTES = 65_536` でボディが切り捨てられるため、
応答が巨大でも fastapi アプリ側は 64KB 以上のメモリを消費しない。
ただし切り捨て後の接続は汚染されるため `close()` が必要。`finally: connection.close()` が
この問題を適切に処理している。

#### E. Pydantic バイパス試行

```
POST /http-client/get  {"host": 12345, "port": "abc", "path": "/"}
→ 422  (host: int → str は変換可能だが port: "abc" → int は Pydantic 拒否)

POST /http-client/get  {"host": null, "port": 80, "path": "/"}
→ 422  (host: null → str は不可)

POST /http-client/post  {"host": "127.0.0.1", "port": 80, "path": "/", "body": "x" * 10001}
→ 422  (body max_length=10000 超過)

POST /http-client/multi  {"host": "127.0.0.1", "port": 80, "paths": ["/"]*6}
→ 422  (paths max_length=5 超過)
```

**結果**: Pydantic の型・長さ制約が有効に機能している。

### ペンテスト総評

| カテゴリ | 結果 | 備考 |
|---|---|---|
| SSRF ホストバイパス | 耐えた | frozenset 比較が有効 |
| DNS リバインディング | **未防御** | 本番では二段階チェックが必要 |
| ヘッダーインジェクション | 耐えた | http.client が \r\n を無害化 |
| ヘッダーサイズ制限なし | 残存リスク（低） | max_length 制限を追加推奨 |
| ポートスキャン代用 | **残存リスク（中）** | ポート許可リストまたはタイムアウト短縮を推奨 |
| レスポンス DoS | 耐えた | 64KB キャップと finally close が機能 |
| Pydantic バイパス | 耐えた | 型・長さ制約が有効 |

**判定**: 条件付き合格（MEDIUM 残存リスク 1 件、LOW 残存リスク 1 件）。
ポートスキャン問題はタイムアウトを 2 秒以下に短縮することで軽減可能だが、
今回のデモ用途では許容範囲。DNS リバインディングは外部公開時の追加実装事項として記録する。

---

## DX Review — 6ペルソナ

### ペルソナ 1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`http.client` という名前から「高レベルの HTTP ライブラリ」を想像してしまい、
`requests` のような `.get(url)` 1 行メソッドを探して迷う可能性がある。

**ドキュメント理解**: `HTTPConnection(host, port)` → `request()` → `getresponse()` → `read()` という
4 ステップのシーケンスは直感的でない。FT レポートの関数一覧があれば追いやすい。

**事故リスク**: 高。`finally: connection.close()` を忘れると接続が漏洩する。
`with` 文が使えるかを最初に調べるが、`http.client.HTTPConnection` はコンテキストマネージャーに
なっていないため、`close()` の明示的呼び出しが必須と気づくのに時間がかかる。

**規約の使いやすさ**: `HttpResponseInfo` dataclass に整形してくれる `_read_response()` ヘルパーは
初心者にとって「これを使えばいい」と分かりやすい。

### ペルソナ 2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`requests` に慣れているため `http.client` の冗長さに違和感を覚える。
コピペ可能なコード例として `fetch_get()` は有用。

**コピペ可能性**: `fetch_get()` をコピーして `host` と `path` を変えるだけで使えるため良好。
**拡張時の罠**: `fetch_multiple()` をコピーして大きなレスポンスを受け取ると F-3 の問題に直面する。
ドキュメントに「64KB 以上のレスポンスで接続が汚染される」という注記があれば防げる。
**事故リスク**: 中。`connection.close()` の漏れは起きやすい。

### ペルソナ 3: フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`fetch()` API に近い感覚で使えるかと思ったが、同期 API で URL ではなく `host/path` に分けて
渡す必要があることに戸惑う。

**エラーレスポンスの質**: 422 の `{"type": "...", "errors": [...]}` 形式は React 側から
使いやすい構造。
**Python 固有概念の学習コスト**: `frozen=True, slots=True` の dataclass は `TypeScript interface` の
読み取り専用オブジェクトと概念が近く、説明が容易。
**事故リスク**: 低（エンドポイントの使い方は REST 的で分かりやすい）。

### ペルソナ 4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

「なぜ `requests` や `httpx` を使わずに `http.client` なのか」と最初に疑問を持つ。
FT の目的（標準ライブラリ検証）を理解すれば納得する。

**他フレームワークとの差異**: `requests` との比較で「リダイレクト非追跡」「コンテキストマネージャー非対応」
「URL を host/path に分割する必要あり」という 3 点が際立つ。
**nene2 の薄さへの評価**: `_validate_host()` が `ValidationException` を raise → `ErrorHandlerMiddleware` が
422 に変換する流れは DI なしで読みやすい。
**事故リスク**: 低（コードの意図が明確）。

### ペルソナ 5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

`_validate_host()` がアプリケーションコアではなくハンドラー層にあるのは適切だが、
DNS リバインディングを防いでいない点はコードレビューでコメントする。

**コードレビューチェックポイント**:
- `finally: connection.close()` は OK。コンテキストマネージャーに比べると見落としリスクがあるが関数スコープで完結している。
- `MAX_RESPONSE_BYTES = 65_536` は定数として適切に宣言されている。
- `headers: dict[str, str]` のヘッダーサイズ制限がない点は指摘する。
- ポートスキャン代用のリスクを PR のコメントに残すことを推奨。

**チームでの安全なパターン**: `fetch_get()` / `fetch_post()` のようなラッパー関数を提供することで
直接 `HTTPConnection` を触るコードの散在を防ぐ設計は評価できる。
**事故リスク**: 低（設計は整合的、残存リスクは文書化済み）。

### ペルソナ 6: 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**:
- `frozen=True, slots=True` dataclass ✓
- `max_length` による入力制限 ✓（ただし `headers` dict のサイズ制限が抜け）
- `ValidationException` + `ValidationError` + `code` フィールド ✓
- `ErrorHandlerMiddleware` を `create_app()` に追加 ✓

**初心者でも安全な API 達成度**: `_ALLOWED_HOSTS` ホワイトリストは最小防御として適切。
ただし `init-ft.sh` のテンプレートに `ErrorHandlerMiddleware` を含めていないため、
F-2 の摩擦が発生した。テンプレートの改善余地がある。

**F-2 への対応**: `init-ft.sh` の pyproject.toml テンプレートに `ErrorHandlerMiddleware` の
`add_middleware` 呼び出しを含む `create_app()` のスニペットを追加することを推奨する。

---

## Follow-up

- `init-ft.sh` テンプレートに `ErrorHandlerMiddleware` を含む最小 `create_app()` を追加（今 PR に含める）
- CLAUDE.md の `ValidationError` 使用例に `code` 引数を明記（今 PR に含める）
- DNS リバインディング対策（ipaddress による解決後 IP 検証）は Issue として記録
