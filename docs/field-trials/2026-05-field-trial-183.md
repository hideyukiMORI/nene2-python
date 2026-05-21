# FT183: smtplib モジュール

**日付**: 2026-05-21
**テーマ**: SMTP 送信・STARTTLS・ヘッダーインジェクション防御・モック戦略
**セキュリティ診断**: **あり**（183 % 3 = 0）

---

## 概要

Python 標準ライブラリの `smtplib` モジュールを検証する。
FT182（email モジュール）でメッセージ構築を実装したのに続き、
今回は SMTP プロトコルでの実際の送信、STARTTLS/SMTP_SSL による暗号化、
ヘッダーインジェクション防御、サーバー機能確認（EHLO）を実装する。
実際のSMTPサーバーへの接続を必要としない `unittest.mock.patch` を使ったテスト戦略も確立する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft183-smtplib/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `validate_email_address(address)` | メールアドレス基本バリデーション |
| `sanitize_header(value)` | CR/LF 除去でヘッダーインジェクション防御 |
| `is_safe_header(value)` | ヘッダー値が安全か確認（bool） |
| `build_message(payload)` | `EmailPayload` → `EmailMessage`（ヘッダーサニタイズ済み） |
| `send_email(config, payload)` | STARTTLS で SMTP 送信（`SendResult` 返却） |
| `send_email_ssl(config, payload)` | SMTP_SSL（ポート 465）で送信 |
| `check_server(host, port, timeout)` | EHLO で SMTP サーバー機能一覧を取得 |
| `dry_run_send(payload)` | ネットワーク接続なしの検証・構築（テスト・ドキュメント用） |
| `SmtpConfig` | `@dataclass(frozen=True, slots=True)` — SMTP 接続設定 |
| `EmailPayload` | `@dataclass(frozen=True, slots=True)` — 送信データ |
| `SendResult` | `@dataclass(frozen=True, slots=True)` — 送信結果・拒否アドレス |
| `ServerInfo` | `@dataclass(frozen=True, slots=True)` — EHLO 応答 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/dry-run` | 送信しないでメッセージ検証・構築 |
| POST | `/sanitize-header` | CR/LF を除去してヘッダーインジェクション防御 |
| POST | `/validate-address` | メールアドレスのフォーマット検証 |
| POST | `/send` | STARTTLS で SMTP 送信 |
| POST | `/check-server` | SMTP サーバーの EHLO 機能一覧を取得 |

---

## テスト結果

**47 passed**（初回 46 通過 → テスト修正後 47 全通過）

```
47 passed in 0.34s
```

mypy: Success / ruff: All checks passed / pip-audit: PYSEC-2025-183（継続監視）

---

## 摩擦ポイント

### F-1: `unittest.mock.patch("smtplib.SMTP")` はコンテキストマネージャの戻り値を手動設定する必要がある（深刻度: 低）

**事象**: `with patch("smtplib.SMTP", return_value=mock_smtp)` で `smtplib.SMTP()` を
モックしたが、`with smtplib.SMTP(...) as smtp:` の `smtp` が `mock_smtp` ではなく
`mock_smtp.__enter__.return_value` になる。
`smtp.sendmail()` が呼ばれず `AttributeError` が発生した。

**原因**: `MagicMock()` はデフォルトで `__enter__` / `__exit__` を持つが、
`__enter__.return_value` が自動的に `mock_smtp` 自身を返すわけではない。
コンテキストマネージャの `as` 変数は `__enter__()` の戻り値になるため、
`mock.__enter__ = MagicMock(return_value=mock)` と明示的に設定する必要がある。

**対応**:
```python
def _make_mock_smtp() -> MagicMock:
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)  # ← 自身を返す
    mock.__exit__ = MagicMock(return_value=False)
    mock.sendmail = MagicMock(return_value={})
    mock.ehlo_resp = b"mail.example.com"
    mock.esmtp_features = {"starttls": "", "auth": "PLAIN LOGIN"}
    return mock
```

---

## 観察点

### 観察1: smtplib の例外階層は詳細なエラー分類を提供する

```python
smtplib.SMTPException           # 基底クラス
├── SMTPServerDisconnected      # 接続が切れた
├── SMTPResponseException       # サーバーが非2xx を返した
│   ├── SMTPSenderRefused       # MAIL FROM 拒否
│   ├── SMTPRecipientsRefused   # RCPT TO 全拒否
│   ├── SMTPDataError           # DATA フェーズのエラー
│   └── SMTPAuthenticationError # 認証失敗
└── SMTPConnectError            # 接続失敗
```

`SMTPRecipientsRefused` は `sendmail()` が一部の受信者を拒否したときに投げられるが、
一部が成功・一部が失敗の場合は例外ではなく `sendmail()` の戻り値（dict）として返る。
部分成功の検出には返り値チェックが必要。

### 観察2: STARTTLS は `use_starttls=True` 時のみ有効にすること

```python
# 危険: TLS なしで平文送信
smtp = smtplib.SMTP(host, port)
smtp.login(username, password)  # 認証情報が平文で送信される

# 安全: STARTTLS で暗号化してから認証
smtp = smtplib.SMTP(host, port)
smtp.ehlo()
context = ssl.create_default_context()
smtp.starttls(context=context)  # ← TLS アップグレード
smtp.ehlo()                      # ← TLS 後に再度 EHLO
smtp.login(username, password)   # ← 暗号化された認証
```

`starttls()` に `ssl.create_default_context()` を渡すことで証明書検証が有効になる。
デフォルト引数（`context=None`）は SSL コンテキストなしで接続するため非推奨。

### 観察3: SMTP_SSL は `ssl.create_default_context()` で証明書検証が必須

```python
# 危険: 証明書検証なし（MITM 攻撃に脆弱）
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

# 安全: デフォルトコンテキスト（証明書検証あり）
context = ssl.create_default_context()
with smtplib.SMTP_SSL(host, port, context=context) as smtp:
    ...
```

### 観察4: `smtp.sendmail()` の戻り値は拒否アドレスの dict

```python
refused = smtp.sendmail(from_addr, to_addrs, msg_bytes)
# refused = {} → 全員に送信成功
# refused = {"user@example.com": (550, b"User unknown")} → 一部拒否
# SMTPRecipientsRefused 例外 → 全員拒否
```

`sendmail()` の第2引数（recipients）は文字列でも list でも受け付けるが、
戻り値の dict のキーは送信に使った宛先文字列そのもの。
Pydantic で受け取った `list[str]` をそのまま渡すことで型が一致する。

### 観察5: SMTP タイムアウトの設定は接続時のみ

```python
smtp = smtplib.SMTP(host, port, timeout=30.0)
```

`timeout` は TCP 接続のタイムアウト。
`ehlo()` / `starttls()` / `sendmail()` などの各コマンドにも適用される。
`timeout=None` はブロッキングになるため、本番コードでは必ず設定すること。

---

## nene2-python フレームワークとの統合

- `SmtpConfig` は Pydantic `SecretStr` で `password` フィールドをラップするべき — 現状は `str`
- `send_email()` は UseCase の `execute()` メソッド内に閉じ込め、HTTP ハンドラーから直接呼ばない
- `dry_run_send()` は UseCase のユニットテストでメール構築ロジックを検証するのに直接使える
- SMTP ゲートウェイは `EmailGatewayInterface` として抽象化し、テストでは `InMemoryEmailGateway` を注入
- 送信ログには宛先・件名のみ記録し、本文・認証情報は含めない

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

お問い合わせフォームからメールを送信する機能を実装しようとしている。

**ドキュメント理解**: Python Docs の smtplib の例は非常にシンプルで `starttls()` を省いた
危険なサンプルが多い。「STARTTLS を使うと安全」という説明はあるが、
「使わないと何が問題か」を説明するサンプルはドキュメントにない。  
**事故リスク**: 高。`smtp.login(username, password)` を STARTTLS より前に呼ぶと
認証情報が平文でネットワークに流れる。初心者がこの順番を間違えてもエラーは出ない。  
**規約の使いやすさ**: `with smtplib.SMTP(...) as smtp:` の context manager パターンは
明確で理解しやすい。例外の種類が多くて戸惑うが、
`SMTPException` を catch しておけば最低限動く。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

既存のスクリプトを「API 化」しようとしている。
古いブログ記事のコードをそのまま FastAPI に移植する。

**コピペ可能性**: 古い Stack Overflow の回答には `ssl.PROTOCOL_TLS` や
`ssl.PROTOCOL_SSLv23` が使われていることが多く、
Python 3.12 では非推奨警告が出る。`ssl.create_default_context()` を使う記事は比較的新しい。  
**拡張時の罠**: `smtp.ehlo()` を忘れると一部のサーバーで `SMTPException` が出る。
「前のコードで動いていたのに」という状態になりやすい。  
**セキュリティ的な事故リスク**: 高。`timeout` の設定忘れでサーバーが応答しない場合に
スレッドがブロックされる DoS につながる。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

「送信ボタン」→ FastAPI → SMTP の連携を実装している。
sendgrid や AWS SES を使ったことがある。

**エラーレスポンスの質**: `SendResult.refused` に拒否された受信者と理由コードを含める設計は
クライアント側での「どのアドレスが使えないか」の判定に使える。
ただし SMTP のエラーコード（550 など）は HTTP ステータスコードとは別概念で、
フロントエンド側での解釈には説明が必要。  
**Python 固有概念の学習コスト**: SendGrid SDK の `Mail` オブジェクトに慣れていると、
`EmailMessage` + `smtplib.SMTP` の2段構えが冗長に見える。
「構築と送信が分離している設計」の価値を説明する必要がある。  
**事故リスク**: 低。HTTP 境界での Pydantic バリデーションが充実。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `send_mail()` を FastAPI に移植しようとしている。

**他フレームワークとの差異**: Django は `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS` を
`settings.py` で設定し `send_mail()` の1行で送れる。
nene2-python では `SmtpConfig` + `send_email()` の2段構えで「設定と送信の分離」を明示する。
環境変数からの設定注入は自前で実装する必要がある（`AppSettings` パターンが適用可能）。  
**nene2-python の薄さへの評価**: `EmailGatewayInterface` の抽象化パターンは
`smtplib` のモックを排除しながらビジネスロジックのテストを可能にする。
Django の `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` と
同等のものが実装できる。  
**本番投入可能性**: 証明書検証あり TLS・タイムアウト設定・ヘッダーインジェクション防御は
本番品質。認証情報の `SecretStr` 化は本番前の必須対応。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

チームのメンバーが書いたメール送信 PR をレビューしている。

**コードレビューチェックポイント**:
- [x] `starttls()` が `login()` より前に呼ばれているか
- [x] `ssl.create_default_context()` が使われているか（`verify_mode=CERT_NONE` でないか）
- [x] `timeout` が設定されているか（デフォルト `None` = ブロッキング）
- [x] Subject/From/To に `sanitize_header()` が適用されているか
- [x] パスワードが str として引数に渡されていないか（`SecretStr` 推奨）

**チームでの安全なパターン**: `SmtpConfig` の `password` フィールドを
`SecretStr` に変更し、ログに平文が出ないことを保証する。  
**ツール追加の必要性**: `bandit B321`（smtplib 使用の警告）は誤検知が多いため
プロジェクト設定で抑制可能。`ssl.SSLContext.verify_mode == ssl.CERT_NONE` の検出は
`bandit B501/B502` でカバー可能。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 中  
**「初心者でも安全な API」達成度**: 中  
— STARTTLS 順序ミスが「エラーなく動くが危険」な状態を作る。
`SmtpConfig.use_starttls=True` をデフォルトにしているが、
False に変更すると認証情報が平文で送信されることをドキュメント化する必要がある。  
**設計上の負債**: `SmtpConfig.password` が `str` のままで `SecretStr` でない。
ログ出力時に平文が残る可能性がある。  
**Follow-up Issue 候補**: SmtpConfig の password を SecretStr にする

---

## セキュリティ診断（FT183 % 3 = 0）

> **診断方針**: Django・FastAPI・SQLAlchemy 本体でも CVE が報告されてきたレベルの
> 攻撃ベクターを対象とする。「動いているから安全」は不正解。
> 実装ミスが起きやすい箇所を意図的に探し、問題がなければその理由まで記録する。

### 1. OWASP API Security Top 10 (2023)

#### API1: オブジェクトレベルの認可不備 (BOLA / IDOR)
- 認証保護なし — FT183 は SMTP クライアントライブラリのデモで、ユーザーオブジェクトを持たない
- **結果**: 該当なし（認可チェックが必要なリソースが存在しない）

#### API2: 認証の破損 (Broken Authentication)
- `/send` エンドポイントは誰でも呼べる（認証不要）
- 本番用途では Bearer Token 認証が必要だが FT のスコープ外
- **結果**: ⚠️ /send は本番で保護が必要（FT スコープでは許容）

#### API3: オブジェクトプロパティレベルの認可不備 (Mass Assignment)
- Pydantic モデルに定義されていないフィールドは自動無視（Pydantic v2 のデフォルト）
- `{"is_admin": true}` を POST しても無視される
- **結果**: ✅ 問題なし

#### API4: 無制限リソース消費 (Unrestricted Resource Consumption)
- `body: str = Field(max_length=100_000)` — 本文は 100KB に制限
- `to_addresses: list[str] = Field(max_length=100)` — 宛先は 100 件に制限
- `timeout: float = Field(ge=1.0, le=60.0)` — タイムアウトは 1〜60 秒に制限
- **結果**: ✅ 問題なし

#### API5: 機能レベルの認可不備 (Broken Function Level Authorization)
- `/send` は外部の SMTP サーバーに接続できるため、SSRF に近いリスクがある
- **結果**: ⚠️ /send は内部ネットワークの SMTP サーバーへの接続に使われる可能性がある（→F-2）

#### API6: サーバーサイドリクエストフォージェリ (SSRF)
- `/send` の `smtp_host` にユーザーが `127.0.0.1`・`169.254.169.254` を指定できる
- `check_server` の `host` も同様
- 内部 SMTP サービスへのプローブが可能
- **結果**: ⚠️ SSRF リスクあり（F-2 として記録）

#### API7: セキュリティの設定ミス
- CORS は FastAPI のデフォルト（制限なし）— FT スコープでは許容
- デバッグモードのスタックトレース露出なし
- **結果**: ⚠️ CORS 設定は本番前に対応が必要

#### API8 〜 API10
- 古いバージョンのエンドポイントなし・デバッグエンドポイントなし
- **結果**: ✅ 問題なし

---

### 2. インジェクション攻撃

#### SMTP ヘッダーインジェクション
- **攻撃**: Subject に `"Test\r\nBcc: attacker@evil.com"` を送信
- **実装**: `sanitize_header()` が `\r\n` を除去 → `"TestBcc: attacker@evil.com"` に変換
- **テスト**: `test_header_injection_payloads_sanitized` でパラメトライズドテストを実装
- **結果**: ✅ 全攻撃ペイロード耐性あり

```python
# 攻撃
{"subject": "Test\r\nBcc: attacker@evil.com"}
# sanitize_header() 後
Subject: TestBcc: attacker@evil.com  # ← 単一行のまま（注入失敗）
```

#### コマンドインジェクション
- `subprocess`・`os.system` は使用していない
- **結果**: ✅ 問題なし

#### パストラバーサル
- ファイルシステムアクセスなし
- **結果**: ✅ 該当なし

---

### 3. 認証・認可

- `SmtpConfig.password` は `str` 型 — `SecretStr` でないためログに平文が出る可能性
- タイミング攻撃: SMTP 認証は `smtplib` に委ねているため実装依存
- **結果**: ⚠️ パスワードの `SecretStr` 化が必要（F-3 として記録）

---

### 4. 入力バリデーション

```python
# テスト入力
Subject: "A" * 999     # max_length=998 → Pydantic が 422 を返す ✅
smtp_host: "" * 0      # 空文字 → check_server で None を返す ✅
smtp_port: 0           # ge=1 → Pydantic が 422 を返す ✅
smtp_port: 65536       # le=65535 → Pydantic が 422 を返す ✅
timeout: 0.5           # ge=1.0 → Pydantic が 422 を返す ✅
to_addresses: [] * 101 # max_length=100 → Pydantic が 422 を返す ✅
```

- 全フィールドに `max_length` / `ge` / `le` 制限あり
- **結果**: ✅ 問題なし

---

### 5. 情報漏洩

- SMTPAuthenticationError のエラーメッセージには SMTP レスポンスコード（535 等）のみを含む
- パスワードはエラーメッセージに含まれない
- **結果**: ✅ 問題なし（パスワード自体は SecretStr 化を推奨 — F-3）

---

### 6. Python / FastAPI 固有の攻撃ベクター

#### ReDoS
- `_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")`
- `^` と `$` でアンカーされており、バックトラッキングの爆発は限定的
- `max_length=254` が先行してチェックされるため入力上限あり
- **結果**: ✅ 問題なし

#### pickle / yaml
- 使用なし
- **結果**: ✅ 問題なし

#### 非同期レースコンディション
- 全エンドポイントが同期関数 — グローバル状態への書き込みなし
- **結果**: ✅ 問題なし

#### 型強制攻撃 (Pydantic Type Coercion)
- `use_starttls: bool` に `"yes"` を送ると `True` に変換される — 意図通り
- `smtp_port: int` に `"587"` を送ると `587` に変換される — 意図通り
- **結果**: ✅ 問題なし（意図した変換）

#### SSRF（/send・/check-server エンドポイント）
```
smtp_host: "127.0.0.1"           → 内部 SMTP サービスにアクセス可能
smtp_host: "169.254.169.254"      → AWS メタデータへの接続試行
smtp_host: "192.168.1.1"          → 内部ネットワークへの接続
host: "127.0.0.1", port: 6379     → Redis のプローブ（SMTP プロトコルなので応答は失敗）
```

`/check-server` は EHLO を試みるため、任意ホストへの TCP 接続を誘発できる。
ただし SMTP プロトコルでのやり取りのみで、HTTP リクエストや恣意的なデータ送信はできない。
**結果**: ⚠️ 内部ネットワークのポートスキャンに悪用される可能性あり（F-2）

---

### 7. 依存関係の脆弱性スキャン

```
Name  Version ID             Fix Versions
----- ------- -------------- ------------
pyjwt 2.12.1  PYSEC-2025-183 （修正版なし）
```

- PYSEC-2025-183: PyJWT の mcp 依存経由の推移的脆弱性
- **対応方針**: mcp ライブラリ側の修正を待ち。継続監視中

---

### 診断サマリー

| カテゴリ | 結果 | 最重要発見 |
|---|---|---|
| OWASP API Security Top 10 | ⚠️ 3件要対応 | /send の認証なし・SSRF リスク |
| SMTP ヘッダーインジェクション | ✅ 全通過 | sanitize_header() で防御済み |
| コマンドインジェクション | ✅ 問題なし | - |
| パストラバーサル | ✅ 該当なし | - |
| 認証・認可 | ⚠️ | SmtpConfig.password が str |
| 入力バリデーション | ✅ 問題なし | 全フィールドに制限あり |
| 情報漏洩 | ✅ 問題なし | コード番号のみ返す |
| ReDoS | ✅ 問題なし | アンカー + max_length 保護 |
| pickle / yaml | ✅ 問題なし | - |
| 非同期レースコンディション | ✅ 問題なし | - |
| 型強制攻撃 | ✅ 問題なし | - |
| 依存関係 CVE | ⚠️ | PYSEC-2025-183（継続監視） |

**総合評価**: 条件付き合格（F-2・F-3 を次 FT までに対応）  
**発見した脆弱性**: 3件（CRITICAL: 0 / HIGH: 0 / MEDIUM: 2 / LOW: 1）  
**新規セキュリティ Issue**: #513（SSRF）、#514（SecretStr）

---

## 摩擦ポイント（セキュリティ診断由来）

### F-2: `/send`・`/check-server` で任意ホストへの TCP 接続が可能（深刻度: 中）

**事象**: `smtp_host: "127.0.0.1"` を送ると内部サービスへの接続を試みる。
内部 SMTP がない場合でも接続試行（タイムアウトまで）が行われる。

**対応**: ホスト名の許可リスト制限、または Private IP アドレスブロック（RFC 1918）の拒否:
```python
import ipaddress

_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
]

def is_ssrf_safe_host(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
        return not any(addr in network for network in _PRIVATE_RANGES)
    except ValueError:
        return True  # ホスト名はドメイン名バリデーションに委ねる
```

### F-3: `SmtpConfig.password` が `str` 型でログに平文が残る可能性（深刻度: 低）

**事象**: `SmtpConfig(password="secret")` を `repr()` / `str()` するとパスワードが平文で出力される。
FastAPI のアクセスログやデバッグプリントで漏洩する可能性がある。

**対応**: Pydantic の `SecretStr` で保護する:
```python
from pydantic import SecretStr

# HTTP リクエストボディで受け取る場合
class SendRequest(BaseModel):
    password: SecretStr  # repr では '**********' と表示される

# UseCase に渡す場合
config = SmtpConfig(password=body.password.get_secret_value())
```

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 中 | [FT183] /send・/check-server の SSRF 対策（Private IP ブロック） | security |
| 低 | [FT183] SmtpConfig.password を SecretStr に変更 | security |

---

## まとめ

FT183 では `smtplib` モジュールを中心に、SMTP 送信・TLS・ヘッダーインジェクション防御・
EHLO サーバー確認を実装した。47 テストが全通過し、mypy/ruff も問題なし。

セキュリティ診断（FT183 % 3 = 0）では2件の MEDIUM 指摘を発見:
- F-2: `/send`・`/check-server` の SSRF リスク（Private IP への接続制御が未実装）
- F-3: `SmtpConfig.password` が `str` のため `SecretStr` 化が必要

ヘッダーインジェクション防御（`sanitize_header()`）はパラメトライズドテストで
4種類の攻撃ペイロードに対して耐性を確認済み。

v1.8.54 としてリリース。
