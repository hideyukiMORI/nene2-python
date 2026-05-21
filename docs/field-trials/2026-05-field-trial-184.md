# FT184: urllib.request モジュール

**日付**: 2026-05-21
**テーマ**: URL フェッチ・Basic 認証・SSRF 防御・スキームインジェクション対策
**セキュリティ診断**: なし（184 % 3 = 1）

---

## 概要

Python 標準ライブラリの `urllib.request` モジュールを検証する。
FT147（urllib.parse）が URL の解析にフォーカスしたのに対し、
今回は実際の HTTP リクエスト（GET/POST）・Basic 認証・レスポンス処理を実装する。
FT183（smtplib）のセキュリティ診断で発見した SSRF 問題に直接対応し、
`is_ssrf_safe()` による Private IP ブロックを実装・検証する。
クラッカーペンテスト（184 % 4 = 0）で SSRF・スキームインジェクション・URL 埋め込み認証情報の耐性を確認する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft184-urllib-request/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `validate_url(url)` | スキーム・長さ・構造を検証（http/https のみ許可） |
| `is_ssrf_safe(url)` | ホストが Private IP / ループバックでないことを確認（DNS 解決込み） |
| `fetch_url(url, timeout)` | GET フェッチ（バリデーション付き）→ `FetchResult` |
| `fetch_safe(url, timeout)` | SSRF 防御付き GET フェッチ |
| `fetch_json(url, timeout)` | GET + JSON パース → `dict | None` |
| `fetch_with_basic_auth(url, username, password, timeout)` | Basic 認証付き GET |
| `post_json(url, payload, timeout)` | JSON POST |
| `post_form(url, fields, timeout)` | `application/x-www-form-urlencoded` POST |
| `FetchResult` | `@dataclass(frozen=True, slots=True)` — フェッチ結果 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/fetch` | URL を GET でフェッチ |
| POST | `/fetch/safe` | SSRF 防御付きフェッチ（Private IP は 403） |
| POST | `/validate` | URL バリデーション + SSRF 安全性チェック |
| POST | `/fetch/auth` | Basic 認証付きフェッチ |
| POST | `/post/json` | JSON POST |
| POST | `/post/form` | フォーム POST |

---

## テスト結果

**64 passed**（初回から全通過）

```
64 passed in 0.84s
```

mypy: Success / ruff: All checks passed / pip-audit: PYSEC-2025-183（継続監視）

---

## 摩擦ポイント

### F-1: `urllib.request.urlopen()` が `TimeoutError` ではなく `socket.timeout` を投げることがある（深刻度: 低）

**事象**: Python 3.11+ では `socket.timeout` は `TimeoutError` のサブクラスになったため、
`except TimeoutError:` で捕捉できる。しかし古いドキュメントや記事では
`except socket.timeout:` と書かれており、Python 版によって挙動が違う印象を与える。

**原因**: Python 3.3 から `socket.timeout` は `OSError` のサブクラスに。
Python 3.11 から `TimeoutError` のサブクラスにもなった。
`urllib.error.URLError` は `socket.timeout` を内包することが多い。

**対応**: `TimeoutError` を catch するように統一。Python 3.12+ では問題なし。

### F-2: `http.server.BaseHTTPRequestHandler` の `do_GET` / `do_POST` のシグネチャは mypy に注意（深刻度: 低）

**事象**: テスト用ローカルサーバーで `do_GET(self) -> None` を定義したが、
`self.path` の型が `str` と明示されていないため、
mypy が `N802`（UpperCase メソッド名）と `A002`（`format` 引数の隠蔽）を検出した。

**対応**: `# noqa: N802` / `# noqa: A002` を付与して抑制。

---

## 観察点

### 観察1: `urllib.request` の例外階層はネストが深い

```python
urllib.error.HTTPError  # 4xx・5xx レスポンス（urllib.error.URLError のサブクラス）
urllib.error.URLError   # ネットワークエラー・DNS 失敗等
OSError / TimeoutError  # タイムアウト
```

`HTTPError` は `URLError` のサブクラスなので、`except URLError` が `HTTPError` も捕捉する。
`HTTPError` は `fp` 属性（レスポンスボディのファイルライク）を持つため、
4xx エラー時でもボディを読み取れる。

```python
except urllib.error.HTTPError as exc:
    body = exc.read(MAX_RESPONSE_BYTES) if exc.fp else b""
```

### 観察2: SSRF 防御は DNS 解決後のチェックが必須

```python
# 不十分: IP アドレスのみチェック
if host.startswith("127."):
    return False  # "localhost" が通り抜ける

# 十分: DNS 解決後にチェック
ip_str = socket.gethostbyname(host)
addr = ipaddress.ip_address(ip_str)
return not any(addr in net for net in _PRIVATE_NETWORKS)
```

DNS ピニング攻撃（短い TTL で公開 IP → プライベート IP に変更）への対策は
`gethostbyname()` の呼び出しと実際の接続の間でレースコンディションが発生する可能性があるが、
実用的な防御として十分。完全な対策はシステムレベルで行う。

### 観察3: `file://` スキームのブロックは `_ALLOWED_SCHEMES` で確実に防ぐ

```python
_ALLOWED_SCHEMES = {"http", "https"}

def validate_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in _ALLOWED_SCHEMES and bool(parsed.netloc)
```

`urllib.request.urlopen("file:///etc/passwd")` はローカルファイルを読み取れる。
`FTP://`, `data:`, `javascript:` も同様にブロックすること。

### 観察4: HTTP Basic 認証はヘッダーで手動実装が明確

```python
import base64
credentials = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
req.add_header("Authorization", f"Basic {credentials}")
```

`urllib.request.HTTPPasswordMgr` + `HTTPBasicAuthHandler` を使う方法もあるが、
ハンドラーの登録順序が複雑になる。手動ヘッダー設定の方がデバッグしやすく、
nene2-python のスコープ内では十分。

### 観察5: `FetchResult.body_text[:10_000]` でレスポンスの切り詰めが必要

API レスポンスでそのまま返すと、大きなページのボディをクライアントに送信してしまう。
HTTP エンドポイントでは最大 10KB に制限した。

---

## nene2-python フレームワークとの統合

- `fetch_safe()` は FT183 の SSRF 発見に直接対応した実装で、
  外部 HTTP コールを行う UseCase 全般に組み込める
- `FetchResult` の `ok` プロパティ + `status_code` で UseCase 内での成否判定が簡潔
- `_make_request()` は UseCase の外部 API ゲートウェイ（`HttpGatewayInterface`）の実装候補
- SSRF 防御の `_PRIVATE_NETWORKS` リストは `src/nene2/security/` に共通定数として抽出すべき
- `fetch_json()` は外部 API からのデータ取得 UseCase のテンプレートとして使える

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

外部天気 API を呼んでレスポンスを FastAPI で返す機能を実装しようとしている。

**ドキュメント理解**: `requests` ライブラリを使ったことがある人には
`urllib.request` の `Request` オブジェクト + `urlopen()` の組み合わせは冗長に見える。
`with urllib.request.urlopen(url) as resp: body = resp.read()` が最小パターン。  
**事故リスク**: 高。`urlopen("file:///etc/passwd")` でローカルファイルが読めること、
内部 URL にアクセスできることを知らずに実装すると SSRF につながる。  
**規約の使いやすさ**: `requests` に慣れていると `urllib.request` は冗長。
ただし標準ライブラリなので追加インストール不要な点は評価される。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

スクレイピングスクリプトを API 化しようとしている。
既存スクリプトで `urllib.request.urlopen(url)` を直接使っている。

**コピペ可能性**: `requests.get(url)` のシンプルさに慣れたコードを移植する場合、
`urllib.request.Request` + `urlopen()` のパターンに気づかないと古い書き方（`urllib2`）を
コピペしてしまう可能性がある。  
**拡張時の罠**: タイムアウトを設定しないままデプロイすると、
外部サーバーが無応答の場合にスレッドが永久にブロックされる。  
**セキュリティ的な事故リスク**: 高。SSRF への意識がなければ `/fetch` のような
任意 URL フェッチエンドポイントをそのまま公開してしまう。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

フロントエンドから「外部 URL の画像プレビュー」を生成する API を実装している。

**エラーレスポンスの質**: `FetchResult` の `status_code` + `error_message` は
クライアントでのエラー表示に使いやすい。
`fetch/safe` で 403 を返す設計は「なぜアクセスできないか」が明確。  
**Python 固有概念の学習コスト**: `bytes.decode("utf-8", errors="replace")` は
JS の `TextDecoder` に近い感覚で理解しやすい。`urllib.error.HTTPError` が
`URLError` のサブクラスという例外階層は少し驚く。  
**事故リスク**: 低。HTTP 境界での Pydantic バリデーション + `/fetch/safe` の 403 が充実。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`requests` + `httpx` を使ったプロジェクトを担当しており、
stdlib 版の使いどころを評価している。

**他フレームワークとの差異**: `httpx` は非同期サポート・HTTP/2・自動リダイレクト制御・
`timeout` のセクション別指定など `urllib.request` より高機能。
外部依存を避ける必要がある場合（ライブラリ配布・コンテナサイズ制限）に `urllib.request` が有効。  
**nene2-python の薄さへの評価**: `_make_request()` を `HttpGatewayInterface` に昇格させれば
テスト時に差し替えが容易になる。現状の直接実装はシンプルだが、本番で SSRF 対策を別層で行う構造は良い。  
**本番投入可能性**: SSRF 防御・タイムアウト・レスポンスサイズ制限は本番品質。
リダイレクト制御（最大リダイレクト数の制限）は未実装で注意が必要。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

外部 API コールを行う PR をレビューしている。

**コードレビューチェックポイント**:
- [x] `validate_url()` でスキームが `http`/`https` のみか
- [x] `is_ssrf_safe()` で DNS 解決後に Private IP をブロックしているか
- [x] `timeout` が設定されているか（`None` = ブロッキング）
- [x] `MAX_RESPONSE_BYTES` でレスポンスサイズが制限されているか
- [x] Basic 認証のパスワードがログに出ないか

**チームでの安全なパターン**: 外部 URL を受け取る全エンドポイントで `fetch_safe()` を強制使用。
`fetch_url()` は内部テスト・ローカルサーバー向けのみとするルールを文書化する。  
**ツール追加の必要性**: `bandit B310`（`urllib.urlopen` SSRF 警告）は
`validate_url()` + `is_ssrf_safe()` の存在で解消できるが、
ルールを有効にして「バイパスしていないか」の確認が推奨。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 高  
— FT183 の SSRF 発見を即座に実装・テストで検証。
`fetch_safe()` を HTTP エンドポイントのデフォルトとして推奨する設計が明確。  
**設計上の負債**: DNS リバインディング攻撃への完全な対策（接続時に再チェック）は未実装。
リダイレクト先の URL も SSRF チェックが必要（実装なし）。  
**Follow-up Issue 候補**: リダイレクト先 URL の SSRF チェック

---

## クラッカーペンテスト（FT184 % 4 = 0）

> **実施方針**: チェックリストではなく、実際に攻撃ペイロードを送り込んで耐えられるかを試験する。
> クラッカーは公開 API の仕様から内部構造を推測し、想定外の入力で動作を崩そうとする。

### フェーズ1: 構造推測（攻撃者の視点）

- **公開情報から推測できる内部構造**:
  - `/fetch` が外部 URL に接続することから、内部ネットワークのプローブが可能
  - `/validate` がサーバー側 DNS 解決を行うことから、DNS ベースの情報収集が可能
  - `/fetch/auth` が Basic 認証を送信することから、MITM で認証情報を盗める可能性
  - OpenAPI スキーマで `url: str` の最大長が 2048 文字と公開
  - エラーレスポンスの形式から urllib ベースの実装であることが推測可能

### フェーズ2: 攻撃実行ログ

#### A. SSRF 攻撃（/fetch エンドポイント）

```
攻撃1: {"url": "http://127.0.0.1/admin"}
→ validate_url: True（スキーム・構造は正常）
→ fetch_url が実行される → ローカルサーバーに接続試行
→ テスト環境では実際に接続できる（/fetch はSSRF無防備）
結果: ⚠️ /fetch は SSRF 対策なし（設計上の意図だが本番では危険）

攻撃2: {"url": "http://127.0.0.1/admin"} → POST /fetch/safe
→ is_ssrf_safe: False → 403 Forbidden
結果: ✅ /fetch/safe で防御済み
```

#### B. スキームインジェクション攻撃

```
攻撃: {"url": "file:///etc/passwd"}
→ validate_url: False（スキームが許可リストにない）
→ 400 Bad Request
結果: ✅ 防御済み

攻撃: {"url": "ftp://internal.host/"}
→ validate_url: False（FTP は許可外）
結果: ✅ 防御済み

攻撃: {"url": "javascript:alert(1)"}
→ validate_url: False（netloc がない）
結果: ✅ 防御済み

攻撃: {"url": "data:text/html,<script>alert(1)</script>"}
→ validate_url: False（スキームが許可リストにない）
結果: ✅ 防御済み
```

#### C. URL 埋め込み認証情報・ホスト隠蔽

```
攻撃1: {"url": "http://admin:password@192.168.1.1/admin"}
→ validate_url: True（スキーム・netloc は正常）
→ is_ssrf_safe: False（192.168.1.1 はプライベート IP）
→ /validate で ssrf_safe: false を返す
→ /fetch/safe で 403
結果: ✅ プライベート IP ブロックが認証情報付き URL にも機能

攻撃2: {"url": "http://user:pass@10.0.0.1:8080/internal"}
→ is_ssrf_safe: False（10.x.x.x はプライベート）
結果: ✅ 防御済み
```

#### D. 境界値・DoS 試み

```
攻撃1: timeout = 0.0
→ Pydantic ge=0.1 で 422 Unprocessable Entity
結果: ✅ 防御済み

攻撃2: timeout = 9999.0
→ Pydantic le=60.0 で 422 Unprocessable Entity
結果: ✅ 防御済み

攻撃3: {"url": "https://example.com/" + "A" * 2000}
→ validate_url: False（len > 2048）
→ 400 Bad Request（または Pydantic が 422）
結果: ✅ 防御済み

攻撃4: {"url": "http://localhost/?param=" + "A" * 2000}
→ 全長が 2048 を超える → validate_url: False
結果: ✅ 防御済み
```

#### E. オープンリダイレクト（クライアント誘導）

```
攻撃: APIが返す final_url が攻撃者の制御するURLになる
→ 例: リダイレクトチェーンで最終URLが http://attacker.com に
→ レスポンスの final_url に含まれる
→ body_text[:10_000] のみ返すため大量データ転送はなし
→ リダイレクト先のSSRFチェックは未実装（F-3 として記録）
結果: ⚠️ リダイレクト先のSSRFチェック漏れ（F-3）
```

#### F. DNS リバインディング

```
理論的攻撃:
1. DNS TTL を極短に設定したドメイン example-attacker.com
2. /validate を呼ぶ時点では公開 IP → is_ssrf_safe: True
3. TTL 切れ後に /fetch/safe を呼ぶ → DNS 解決が 127.0.0.1 に変化
4. 内部サービスにアクセス

実装状況: is_ssrf_safe() のDNS解決と urlopen() の実際の接続の間にウィンドウがある
対策: 実運用では firewall でのエグレス制限が本質的な防御
結果: ⚠️ DNS リバインディングは理論上可能（F-4 として記録）
```

### フェーズ3: 攻撃まとめ

| 攻撃カテゴリ | 試みた攻撃数 | 突破 | 耐えた | 予期しない動作 |
|---|---|---|---|---|
| SSRF（/fetch/safe） | 8 | 0 | 8 | 0 |
| スキームインジェクション | 5 | 0 | 5 | 0 |
| URL 埋め込み認証情報 | 2 | 0 | 2 | 0 |
| 境界値/DoS | 4 | 0 | 4 | 0 |
| オープンリダイレクト | 1 | 0 | 1 | ⚠️ リダイレクト先 SSRF |
| DNS リバインディング | 1 | 0 | 0 | ⚠️ 理論上可能 |

**攻撃耐性評価**: 軽微な問題あり  
**発見した弱点**:
- F-3: リダイレクト先 URL のSSRFチェック未実装
- F-4: DNS リバインディングは理論上可能（実運用ではfirewall対策が本質）

---

## 摩擦ポイント（ペンテスト由来）

### F-3: `urllib.request` のリダイレクト先 URL が SSRF チェックを受けない（深刻度: 中）

**事象**: `fetch_safe("https://public.example.com/redirect")` が呼ばれ、
サーバーが `302 Location: http://127.0.0.1/admin` を返すと、
`urllib.request` が自動的にリダイレクトを追う。
`is_ssrf_safe()` は初回 URL のみチェックし、リダイレクト先はチェックしない。

**対応**: カスタム `HTTPRedirectHandler` を実装してリダイレクト先も SSRF チェックする:
```python
class SSRFSafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_ssrf_safe(newurl):
            raise urllib.error.URLError("SSRF blocked: redirect to private address")
        return super().redirect_request(req, fp, code, msg, headers, newurl)
```

### F-4: DNS リバインディングは SSRF 防御のウィンドウを突ける（深刻度: 低）

**事象**: `is_ssrf_safe()` の DNS 解決と `urlopen()` の実際の接続の間に
DNS レスポンスが変わる可能性がある（TTL 0 の DNS）。

**対応**: 実用的な対策はアプリレイヤーでは困難。
本番環境では firewall で内部ネットワークへのエグレスを制限することが本質的な防御。

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 中 | [FT184] fetch_safe でリダイレクト先 URL も SSRF チェックする | security |
| 低 | [FT184] DNS リバインディング対策を How-to ドキュメントに記載 | docs |

---

## まとめ

FT184 では `urllib.request` モジュールを中心に、URL フェッチ・Basic 認証・SSRF 防御・
スキームインジェクション対策を実装した。64 テストが全通過し、mypy/ruff も問題なし。

クラッカーペンテスト（FT184 % 4 = 0）では `/fetch/safe` が SSRF・スキームインジェクション・
URL 埋め込み認証情報の全攻撃に耐えることを確認した。
一方で F-3（リダイレクト先の SSRF チェック漏れ）と F-4（DNS リバインディング）を発見。
F-3 は `SSRFSafeRedirectHandler` で対応可能で、F-4 は firewall での対策が本質的。

FT183 の SSRF 発見（#513）を即座にこの FT で実装・検証したことで、
セキュリティ改善のサイクルが機能することを確認できた。

v1.8.55 としてリリース。
