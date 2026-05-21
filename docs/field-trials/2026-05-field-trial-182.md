# FT182: email モジュール

**日付**: 2026-05-21
**テーマ**: MIME メッセージ構築・ヘッダーエンコード・パース・アドレス操作
**セキュリティ診断**: なし（182 % 3 = 2）

---

## 概要

Python 標準ライブラリの `email` モジュールを検証する。
プレーンテキスト・HTML・添付ファイル付きメールの構築、RFC 2047 ヘッダーエンコード、
生バイト列からのパース、アドレスのバリデーション・整形を網羅する。
FastAPI エンドポイントとして実装し、インプット検証と添付ファイルの安全な扱いまで確認する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft182-email/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `validate_email_address(address)` | メールアドレスの基本フォーマット検証（RFC 5322 簡易正規表現） |
| `parse_address(header_value)` | `'Display Name <email>'` 形式をパース |
| `extract_addresses(header_value)` | カンマ区切りのアドレスリストをパース |
| `encode_header_value(text, charset)` | 非 ASCII を RFC 2047 Base64 エンコード |
| `decode_header_value(encoded)` | RFC 2047 エンコードをデコード |
| `build_simple_email(...)` | `EmailMessage` でプレーンテキストメールを構築 |
| `build_html_email(...)` | `MIMEMultipart("alternative")` で HTML メールを構築 |
| `build_email_with_attachment(...)` | `MIMEMultipart` + `MIMEBase` で添付ファイル付きメールを構築 |
| `parse_email(raw)` | 生バイト列からメールをパース（`ParsedEmail` 返却） |
| `format_address(display_name, email_address)` | 表示名付きアドレスに整形 |
| `ParsedEmail` | `@dataclass(frozen=True, slots=True)` — パース済みメール |
| `AddressPart` | `NamedTuple` — アドレスの構造化表現 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/build/simple` | プレーンテキストメールを hex で返す |
| POST | `/build/html` | HTML マルチパートメールを hex で返す |
| POST | `/build/attachment` | 添付ファイル付きメールを hex で返す |
| POST | `/parse` | 生メール（hex）をパースして構造化レスポンスを返す |
| POST | `/headers/encode` | RFC 2047 エンコード |
| POST | `/headers/decode` | RFC 2047 デコード |
| POST | `/addresses/extract` | カンマ区切りアドレスリストを構造化パース |
| POST | `/addresses/validate` | メールアドレスのフォーマット検証 |
| POST | `/addresses/format` | 表示名付きアドレスに整形 |

---

## テスト結果

**57 passed**（初回 55 通過 → F-1 修正後 57 全通過）

```
57 passed in 0.37s
```

mypy: Success / ruff: All checks passed / pip-audit: PYSEC-2025-183（継続監視）

---

## 摩擦ポイント

### F-1: `app = create_app()` をルート定義より前に置くと全エンドポイントが 404 になる（深刻度: 高）

**事象**: `app.py` の先頭付近で `router = APIRouter()` を定義し、
`app = create_app()` を呼んでから `@router.post(...)` デコレータを書いた。
TestClient で全エンドポイントが 404 を返す。

**原因**: FastAPI の `include_router()` は呼び出し時点の `router.routes` を
アプリケーションにコピーする。`@router.post(...)` デコレータが実行される前に
`include_router(router)` を呼ぶと、空のルーターを取り込む。
Python モジュールは上から順に実行されるため、
デコレータより前に `app = create_app()` が書かれているとルートが登録されない。

**対応**: `create_app()` 関数の定義と `app = create_app()` の呼び出しをファイルの末尾、
全 `@router.post(...)` デコレータの後に移動した。

```python
# 誤: デコレータより前に include_router が実行される
router = APIRouter()
app = create_app()          # ← この時点でルーターは空

@router.post("/build/simple")
def build_simple_endpoint(...): ...

# 正: デコレータで全ルートが登録された後に include_router を実行
router = APIRouter()

@router.post("/build/simple")
def build_simple_endpoint(...): ...

def create_app() -> FastAPI:
    application = FastAPI(title="FT182 email")
    application.include_router(router)
    return application

app = create_app()          # ← ここで全ルートが含まれる
```

**副次効果**: テストで 404 が出た際に「ルーターが空」と気づくまで
エンドポイント名のタイポ・パスの誤りを疑ってしまった。
診断手順として `python -c "from app import app; print([r.path for r in app.routes])"` が有効。

---

## 観察点

### 観察1: `email` モジュールには 3 つの API が混在する

Python の `email` モジュールは長い歴史を持ち、3 種類のクラスが共存している。

| API | クラス | 用途 |
|---|---|---|
| モダン（Python 3.3+）| `EmailMessage` | シンプルなテキストメール構築に最適 |
| レガシー MIME | `MIMEMultipart`, `MIMEText`, `MIMEBase` | HTML・添付ファイルのマルチパート構築 |
| パース用 | `Message` (`email.message_from_bytes` の返り値) | 受信メールの解析 |

`EmailMessage` は `MIMEMultipart("alternative")` を意識せずに書けるが、
添付ファイルや HTML+テキスト の細かい制御は `MIMEMultipart` の方が明確。
`parse_email()` は `email.message_from_bytes()` が `Message` を返すため、
`is_multipart()` / `walk()` でパートを手動で走査する必要がある。

### 観察2: `parseaddr()` は非常に寛容

```python
from email.utils import parseaddr

parseaddr("alice@example.com")         # → ('', 'alice@example.com')
parseaddr("Alice <alice@example.com>") # → ('Alice', 'alice@example.com')
parseaddr("Not An Email")              # → ('', 'Not')  ← 驚き!
parseaddr("")                          # → ('', '')
```

`parseaddr("Not An Email")` は `('', 'Not')` を返す。
単語の最初の部分を「アドレス」として解釈する。
`addr` が空文字列かどうかでしか「アドレスなし」を検出できず、
不正な文字列でも `None` を返さない。
アプリレベルで `validate_email_address()` による追加チェックが必要。

### 観察3: 添付ファイルのファイル名はサニタイズが必須

```python
safe_filename = re.sub(r"[^\w\-.]", "_", attachment_filename)[:255]
```

`../../etc/passwd` のようなパストラバーサル文字列が `Content-Disposition: attachment; filename=` に
そのまま入るとクライアントが危険な場所に保存する可能性がある。
`re.sub` で英数字・ハイフン・ドット以外を `_` に変換することで無害化する。
`../../etc/passwd` → `__.._.._etc_passwd` となり意図が変わるが、
ファイル名として安全になる。

### 観察4: RFC 2047 エンコードは `email.header` で行うより手動 Base64 が明確

```python
# 標準ライブラリ的な書き方
from email.header import Header
Header("テスト件名", "utf-8")  # → '=?utf-8?b?...' だが使い方が複雑

# 手動 Base64 — 動作が明確
import base64
encoded = base64.b64encode("テスト件名".encode("utf-8")).decode("ascii")
result = f"=?utf-8?B?{encoded}?="
```

`email.header.Header` クラスは行長の自動折り返し機能を持つが、
`make_header()` + `decode_header()` のコンビでデコードしないと復元できない。
手動実装の方が「何を送っているか」が透明で、デバッグしやすい。

### 観察5: `message_from_bytes()` は不正データでも例外を投げない

```python
import email
msg = email.message_from_bytes(b"totally not an email")
# → Message オブジェクトが返る（例外なし）
msg.get("From")  # → None
```

`message_from_bytes()` は入力をどんなバイト列でも解析しようとする。
完全に不正なデータでも `None` ではなく空の `Message` オブジェクトを返す。
`parse_email()` が `None` を返すのは、後段の処理で例外が起きた場合のみ。
「パース失敗」の検出には From/Subject が空かどうかを追加チェックする必要がある。

---

## nene2-python フレームワークとの統合

- `build_simple_email()` / `build_html_email()` は通知メール送信 UseCase の内部実装として直接使える
- `parse_email()` の `ParsedEmail` は `@dataclass(frozen=True, slots=True)` なので UseCase の Output 型として適合
- `validate_email_address()` は HTTP 境界の Pydantic バリデーションと二重防御として有効
- `encode_header_value()` は日本語件名を含む全メール送信で必須になる
- Pydantic `max_length=10_485_760`（hex 換算 5MB）で添付ファイルサイズを HTTP 層で制限
- F-1 の教訓: `create_app()` ファクトリはファイル末尾に置く — nene2-python の全 FT サンドボックスで統一すべきルール

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

「メール送信機能を実装してほしい」と言われ、Python の `email` モジュールを調べている。

**ドキュメント理解**: `gzip.compress()` のような1行APIがなく、`EmailMessage` / `MIMEMultipart` / `MIMEText` を
どれを使えばよいか公式ドキュメントだけでは判断しにくい。
`email.message.Message` と `email.message.EmailMessage` が別クラスなのも混乱の源。  
**事故リスク**: 高。`parseaddr()` が不正なアドレスを「有効」として返す挙動（F-2 相当）を
知らないと、バリデーションをすり抜けた無効アドレスに送信しようとする可能性がある。  
**規約の使いやすさ**: `EmailMessage.set_content()` はシンプルだが、添付ファイルを加えた途端に
`MIMEMultipart` に切り替える必要があり、一貫性がない。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

過去に `smtplib` + `email.mime` を使ったスクリプトをコピーして使ったことがある。

**コピペ可能性**: `MIMEMultipart` + `MIMEText` の組み合わせは古いブログ記事に多い。
ただし `Content-Disposition: attachment; filename=` にユーザー入力をそのまま渡す
サンプルコードが多く、F-1 相当のファイル名インジェクションをそのまま踏む。  
**拡張時の罠**: F-1 (app 配置の問題) は修正後も「なぜ末尾に置くのか」を理解しないまま
他のファイルに同じミスをする可能性が高い。  
**セキュリティ的な事故リスク**: 中。添付ファイル名のサニタイズ漏れは
メールクライアント依存でクライアント側のパストラバーサルになりうる。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

フロントエンドから「送信ボタン」を押したときにメール送信 API を呼ぶ機能を実装している。

**エラーレスポンスの質**: 不正なアドレスや無効 hex に対して 400 を返す設計は良い。
ただし「どのフィールドが不正か」を detail に含めていないため、
クライアント側でのデバッグ（どのフィールドを直せばよいか）が難しい。  
**Python 固有概念の学習コスト**: `bytes.hex()` / `bytes.fromhex()` を API の境界で使うパターンは
JS の `ArrayBuffer` → `Uint8Array` の感覚と近く、理解しやすい。
RFC 2047 の `=?utf-8?B?...?=` 形式は HTTP ヘッダーとは別の概念なので説明が必要。  
**事故リスク**: 低。HTTP 境界での Pydantic バリデーションが充実。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

既存の Django プロジェクトにあるメール送信コードを FastAPI に移植しようとしている。

**他フレームワークとの差異**: Django は `django.core.mail.send_mail()` という高レベル API があり、
SMTP の設定・送信・バックエンド切り替えまでフレームワークが抽象化している。
Python stdlib の `email` モジュールはメッセージ構築のみで、送信は `smtplib` が別。
FastAPI には `django.core.mail` 相当はないため、このような薄い実装が必要になる。  
**nene2-python の薄さへの評価**: メッセージ構築ロジックを UseCase に閉じ込めることで
テストで `smtplib` を使わずにメール内容を検証できる設計は良い。
`SendEmailUseCase` → `EmailGatewayInterface` → `SmtplibEmailGateway` の構造が自然な次ステップ。  
**本番投入可能性**: メッセージ構築は本番品質。送信部分（smtplib/外部SMTP）は別途実装が必要。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

チームのメンバーが書いた「メール送信機能」を PR レビューしている。

**コードレビューチェックポイント**:
- [x] `parseaddr()` の戻り値が空文字列チェックのみで、`validate_email_address()` の追加チェックがあるか
- [x] `Content-Disposition: attachment; filename=` にユーザー入力がサニタイズされているか
- [x] `create_app()` がデコレータより後に呼ばれているか（F-1 の罠）
- [x] `message_from_bytes()` の返り値が None チェックなしに使われていないか（返り値は常に Message）

**チームでの安全なパターン**: メールアドレスは `parseaddr()` 後に必ず `validate_email_address()` を
通す二重チェックを社内標準とすること。  
**ツール追加の必要性**: `app = create_app()` の配置問題は静的解析で検出できない。
`create_app()` を呼ぶ前に `router.routes` が空かどうかをアサートするテストケースを
毎回書くルールにすることで防げる。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 中  
— `parseaddr()` の寛容さと `create_app()` の配置問題は初心者が踏みやすい罠。
特に F-1 は「テストが全部 404」という分かりやすい症状だが、原因に気づくまでが辛い。  
**設計上の負債**: `create_app()` をファイル末尾に置くルールが CLAUDE.md に明記されていない。
FT177 から APIRouter パターンを使い始めているが、この制約はどこにも書かれていない。  
**Follow-up Issue 候補**: CLAUDE.md への `create_app()` 配置ルール追記

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 中 | CLAUDE.md に「`create_app()` はファイル末尾・全デコレータの後に定義する」ルールを追記 | docs |
| 低 | `parseaddr()` の寛容な挙動を How-to ドキュメントに記載（二重チェックパターン） | docs |

---

## まとめ

FT182 では `email` モジュールを中心に、MIME メッセージ構築・ヘッダーエンコード・パース・
アドレス操作を実装した。57 テストが全通過し、mypy/ruff も問題なし。

最大の発見は F-1: `app = create_app()` をルート定義より前に置くと
`include_router()` が空のルーターをコピーして全エンドポイントが 404 になる問題。
FastAPI の `include_router()` がコール時点のスナップショットを取るため、
`app = create_app()` はファイル末尾に置くルールが必要。
この制約を CLAUDE.md に追記することを Follow-up Issue として記録した。

v1.8.53 としてリリース。
