# FT228: urllib.parse — urlparse / urlencode / quote（SSRF 対策）

**日付**: 2026-05-29
**テーマ**: Python `urllib.parse` モジュールの URL 解析・エンコードと SSRF 対策の実装と検証
**セキュリティ診断**: 🔒 あり（228 % 3 = 0）
**クラッカーペンテスト**: 🔍 あり（228 % 4 = 0）

---

## 概要

`urllib.parse` は URL の解析・組み立てを行う標準モジュール。HTTP API でラップする際の最大の課題は **SSRF（Server-Side Request Forgery）** — ユーザー指定 URL をサーバーが fetch する場合、`http://api.example.com@evil.com/` のような **URL パース混乱攻撃**で許可リストを回避し、内部ネットワークやクラウドメタデータ（`169.254.169.254`）へアクセスされる。診断＋ペンテスト両対象の本 FT では、`parsed.hostname` を使った許可リスト方式で混乱攻撃を遮断できるかを検証した。

| API | ユースケース |
|---|---|
| `urlparse(url)` | URL を scheme/netloc/path 等に分解。`hostname` は userinfo/port を除いた純ホスト |
| `urlencode(dict)` | パラメータ辞書をクエリ文字列化（自動エスケープ） |
| `parsed.hostname` / `username` / `password` | 混乱攻撃の検出に使う |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft228-urllib-parse/`

| 関数 | 概要 |
|---|---|
| `parse_url()` | URL を scheme/host/port/path に分解 |
| `validate_url()` | SSRF 対策: scheme 許可リスト + userinfo 拒否 + host 完全一致許可リスト |
| `build_query()` | `urlencode` でクエリ文字列を生成（自動エスケープ） |
| `_parse()` | 長さ・空白/改行を検証してから `urlparse` |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/url/parse` | URL を構成要素に分解 |
| POST | `/url/validate` | SSRF 対策の URL 検証 |
| POST | `/url/query` | クエリ文字列を生成 |

---

## 摩擦点

### F-1: 許可リストは `netloc` ではなく `hostname` に適用する

**観察**: SSRF 対策でホストを許可リスト照合する際、`parsed.netloc` を使うと **userinfo・ポートが混入**する。`http://api.example.com@evil.com/` の `netloc` は `api.example.com@evil.com` で、ここに「`api.example.com` が含まれるか」で判定すると**実接続先 `evil.com` を見逃す**（古典的 SSRF バイパス）。

**対処**: `parsed.hostname`（userinfo/port を除き小文字化された純ホスト）に対し**完全一致**で許可リスト照合する。`http://api.example.com@evil.com/` の `hostname` は `evil.com` なので正しく拒否される。

### F-2: userinfo は存在自体を拒否する

**観察**: `hostname` で判定すれば混乱攻撃は防げるが、防御を多層にするため userinfo（`username`/`password`）の**存在自体**も拒否する。正規の API 呼び出しに URL 埋め込み認証情報は不要。

**対処**: `parsed.username is not None or parsed.password is not None` で 422。

### F-3: 許可リストは完全一致（サフィックス偽装の排除）

**観察**: `host.endswith("example.com")` のような**サフィックス判定は危険** — `api.example.com.evil.com` を通してしまう。

**対処**: `host in ALLOWED_HOSTS`（タプル完全一致）。`api.example.com.evil.com` も `api-example.com` も拒否。許可リスト方式のため `localhost`・`127.0.0.1`・`169.254.169.254` も自動的に弾かれる（IP ベースの SSRF を別途防ぐ場合は ipaddress 判定が必要 → FT234）。

---

## セキュリティ診断 & クラッカーペンテスト

許可ホスト: `api.example.com` / `cdn.example.com`、許可 scheme: `http` / `https`。20 種の URL を投入。

| URL | 判定 | 分類 |
|---|---|---|
| `https://api.example.com/ok` | **ALLOW** | 正規（期待通り） |
| `https://API.EXAMPLE.COM/` | **ALLOW** | 正規（大文字→小文字化） |
| `https://api.example.com:8080/x` | **ALLOW** | 正規（許可ホスト + 任意ポート） |
| `https://api.example.com@evil.com/` | BLOCK 422 | userinfo 混乱（F-1） |
| `https://api.example.com:pass@evil.com/` | BLOCK 422 | userinfo+pass |
| `https://evil.com#@api.example.com/` | BLOCK 422 | fragment トリック |
| `https://evil.com/api.example.com` | BLOCK 422 | path トリック |
| `https://api.example.com.evil.com/` | BLOCK 422 | サフィックス偽装（F-3） |
| `https://api-example.com/` | BLOCK 422 | 類似ホスト |
| `file:///etc/passwd` | BLOCK 422 | scheme（ローカル） |
| `gopher://...` / `ftp://...` | BLOCK 422 | scheme（SSRF 多用） |
| `http://169.254.169.254/...` | BLOCK 422 | クラウドメタデータ IP |
| `https://localhost/` / `https://127.0.0.1/` | BLOCK 422 | 内部ホスト/ループバック |
| `...api.example.com\t/x` / `\n/x` | BLOCK 422 | タブ/改行インジェクション |
| `//api.example.com/x` | BLOCK 422 | scheme 相対（scheme 空） |
| `https:///x` | BLOCK 422 | host 欠落 |
| `https://api.example.com%00.evil.com/` | BLOCK 422 | null バイト |

### まとめ

| 攻撃カテゴリ | 試行 | 突破 | 耐えた |
|---|---|---|---|
| userinfo / fragment / path 混乱 | 4 | 0 | 4 |
| ホスト偽装（サフィックス/類似） | 2 | 0 | 2 |
| scheme（file/gopher/ftp/相対） | 4 | 0 | 4 |
| 内部 IP / メタデータ / localhost | 4 | 0 | 4 |
| 制御文字 / null / host 欠落 | 4 | 0 | 4 |

**総合評価: 合格（17 攻撃すべて遮断、正規 3 件のみ許可）**

`parsed.hostname` + 完全一致許可リスト + userinfo 拒否 + scheme 許可リスト + 空白/改行の事前拒否、の多層で SSRF バイパスを全遮断。クエリ生成は `urlencode` が `&`/`=`/空白を自動エスケープ（`a+b%26c%3Dd`）しパラメータインジェクションを防いだ。

---

## テスト結果

```
9 passed in 0.29s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

URL を分解して検証する流れは追える。`netloc` と `hostname` の違いが SSRF の肝だが、初見では区別がつかない。

**ドキュメント理解**: `hostname` を使う理由（userinfo/port 除外）はコメントで説明。
**事故リスク（高）**: `netloc` や文字列 `in` で判定して混乱攻撃を通してしまう。
**規約の使いやすさ**: allowed/host が返り判定が明快。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

Webhook URL や外部 API 連携で SSRF を作り込みやすい。`validate_url` はコピペで使える。

**コピペ可能性**: 許可リスト方式の検証は流用性が高い。
**拡張時の罠**: `endswith` でホスト判定するとサフィックス偽装を通す。完全一致が必須。
**事故リスク（高）**: メタデータ IP・内部ホストへの SSRF。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`new URL()` に対応するが、JS の `URL` も `username`/`hostname` を持つので概念は近い。

**エラーレスポンスの質**: 不正 URL は 422 Problem Details で明確。
**Python 固有概念**: `urlparse` の `hostname` 小文字化・`port` の int 化。
**事故リスク（低）**: 許可リスト + 多層検証。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

SSRF は OWASP API Top 10 常連。`hostname` 許可リスト・userinfo 拒否は王道。IP リテラル・DNS リバインディングまで守るなら ipaddress 解決と名前解決後の再検証が要る（FT234 / 既知の http.client 課題）。

**他フレームワークとの差異**: 多くの SSRF 対策ライブラリが同じ構造。標準ライブラリでも `hostname` を使えば堅い。
**nene2 の薄さへの評価**: 薄いラップに許可リスト判定を足す設計は妥当。
**事故リスク（低）**: 17 攻撃遮断を実測。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- ホスト判定に `netloc` ではなく `hostname` を使っているか — userinfo 混乱攻撃。
- 許可リストが**完全一致**か（`endswith`/`in` 禁止）— サフィックス偽装。
- scheme 許可リスト（`file`/`gopher` 等を排除）。
- userinfo の存在拒否・空白/改行の事前拒否。
- IP リテラル / DNS リバインディングを別途考慮しているか（許可リストで未カバーなら ipaddress 検証）。

**チームでの安全なパターン**: `validate_url` を共通化し、外部 fetch の前に必ず通す。
**事故リスク（低）**: 診断＋ペンテストで全遮断を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。許可リスト方式は「許可オリジンを明示」（CORS ポリシー）と同じ思想。
**初心者でも安全な API 達成度**: `hostname` + 完全一致を関数内に隠蔽し、`netloc` 文字列判定の余地を排除。
**改善提案**: `validate_url` を `nene2.http` に「SSRF セーフ URL バリデータ」として昇格し、FT234（ipaddress）と組み合わせて IP リテラル・プライベート範囲も守る統合ガードにする。
