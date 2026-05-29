# FT220: logging — Logger / Handler / Formatter / Filter

**日付**: 2026-05-29
**テーマ**: Python `logging` モジュールの Logger / Handler / Formatter / Filter の実装と検証
**セキュリティ診断**: なし（220 % 3 = 1）
**クラッカーペンテスト**: 🔍 あり（220 % 4 = 0）

---

## 概要

`logging` は Python 標準のロギングフレームワーク。HTTP API でラップし「メッセージを受け取り、Logger → Filter → Formatter → Handler のパイプラインを通して整形済みログ行を返す」パターンを検証した。ロギングは一見地味だが、**ログインジェクション（偽ログ行注入）** と **フォーマット文字列インジェクション** という 2 つの古典的脆弱性を抱えるため、クラッカーペンテスト回（220 % 4 = 0）の題材として適している。

| API | ユースケース |
|---|---|
| `logging.getLogger(name)` | 名前付き Logger の取得（シングルトン） |
| `logging.Handler` サブクラス | 発行レコードのキャプチャ（`_CapturingHandler`） |
| `logging.Formatter` | `%(levelname)s %(message)s` などの整形 |
| `logging.Filter` サブクラス | レコード書き換えによる機密情報の秘匿（`_RedactingFilter`） |
| `Logger.log(level, "%s", arg)` | 遅延フォーマットでの安全なログ発行 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft220-logging/`

### 主要機能

| 関数 / クラス | 概要 |
|---|---|
| `emit_log()` | 指定レベルでログを発行し整形済み行を返す |
| `redact_log()` | `_RedactingFilter` で機密情報を秘匿してから発行 |
| `structured_log()` | `_JsonFormatter` で JSON 構造化ログを発行 |
| `_CapturingHandler` | 発行レコードをメモリに溜める `logging.Handler` |
| `_RedactingFilter` | `password=` / `token:` 等の値を `***REDACTED***` に置換する `logging.Filter` |
| `_JsonFormatter` | `LogRecord` を JSON 1 行に整形する `logging.Formatter` |
| `_capturing()` | Handler をリクエストごとに attach/detach する contextmanager |
| `_sanitize()` | CRLF をエスケープしログ行偽造を防ぐ |

### エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/logging/emit` | レベル指定でログを発行し整形行を返す |
| POST | `/logging/redact` | 機密情報を秘匿して発行 |
| POST | `/logging/structured` | JSON 構造化ログを発行 |

---

## 摩擦点

### F-1: フォーマット文字列インジェクション — `logger.info(user_input)` の罠

**観察**: `logging` は第 1 引数をフォーマット文字列として扱う。`logger.info(user_message)` のように**ユーザー入力を直接第 1 引数に渡す**と、`%s` や `%(name)s` が書式指定子として解釈される。引数を伴わない `%s` を含むメッセージは、出力時（`record.getMessage()`）に `TypeError: not enough arguments for format string` を発生させる。`logging.raiseExceptions` が真（デフォルト）の環境では stderr にトレースが出るうえ、攻撃者が `%(……)s` で `LogRecord` 属性を覗き見できる可能性もある。

**対処**: メッセージは必ず**引数として**渡す。

```python
logger.log(level, "%s", safe)   # ✅ user 入力は引数。書式指定子は評価されない
# logger.log(level, safe)       # ❌ user 入力が書式文字列になる
```

ペンテストで `%s%s%s` / `%(asctime)s` / `%d` を送り込んだが、すべてリテラル文字列として出力され、例外も情報漏洩も発生しなかった（フェーズ2 C 参照）。

---

### F-2: ログインジェクション — CRLF による偽ログ行の注入

**観察**: ログメッセージに `\n` / `\r` を含めると、ログファイル上で**偽のログ行を捏造**できる。例: `"ok\nCRITICAL admin breach detected"` は、行指向のログビューアやSIEM上では独立した CRITICAL 行に見える。監査ログの信頼性を破壊する古典的攻撃。

**対処**: ログ発行前に改行をエスケープする `_sanitize()` を必ず通す。

```python
return message.replace("\r", "\\r").replace("\n", "\\n")
```

`"ok\nCRITICAL fake breach"` → `INFO ok\nCRITICAL fake breach`（改行はリテラル `\n` 2 文字に変換）。偽行注入は成立しなかった。

---

### F-3: `getLogger` のグローバル状態と ruff `LOG001`

**観察**: 当初、リクエストスコープで独立した Logger を作るため `logging.Logger(name)` で直接インスタンス化したところ、ruff の `LOG001`（"Use `logging.getLogger()` to instantiate loggers"）に弾かれた。Python 公式ドキュメントも「Logger は直接生成せず必ず `getLogger()` を使え」と明記している。一方で `getLogger()` は内部マネージャに Logger をグローバル登録するシングルトンであり、**毎リクエストで Handler を `addHandler()` するとハンドラが無限蓄積**し、出力が N 重化する。

**対処**: `getLogger()` で固定名の Logger を取得し、Handler を**リクエストごとに attach → `try/finally` で必ず detach** する contextmanager に切り出した。`propagate = False` でルートロガーへの伝播も止め、本番ログを汚さない。

```python
@contextmanager
def _capturing(name, formatter, *, filters=None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    handler = _CapturingHandler()
    handler.setFormatter(formatter)
    for f in filters or []:
        handler.addFilter(f)
    logger.addHandler(handler)
    try:
        yield logger, handler
    finally:
        logger.removeHandler(handler)   # 蓄積を防ぐため必ず外す
```

`test_no_handler_accumulation_across_requests` で 3 連続リクエストでも 1 行のみ返ることを確認した。

---

## クラッカーペンテスト

### フェーズ1: 構造推測（攻撃者の視点）

- **公開情報から推測できる内部構造**: エンドポイント名（`/logging/emit` `/redact` `/structured`）から Python `logging` ラッパーと推測可能。`logging` を直に使うアプリは①フォーマット文字列インジェクション、②CRLF ログ偽造、③秘匿漏れ、を抱えやすいと当たりを付ける。`level` がパス構造から enum 制限されていそうだと推測。

### フェーズ2: 攻撃実行ログ

#### A. Pydantic バイパス攻撃

```
A1 {"message":"x"}                         # level 欠落
A2 {"level":20,"message":"x"}              # level を int に
A3 {"level":"INFO","message":["a","b"]}    # message を配列に
A4 {"level":"INFO","message":"x","__class__":"evil"}  # 余分フィールド
```
**結果**: A1/A2/A3 はいずれも **422**（Pydantic 型検証で遮断）。A4 は余分フィールドが Pydantic に無視され **200**（`INFO x`）。Mass Assignment の余地なし（BaseModel に該当フィールドが存在せず、`__class__` 等の汚染は起きない）。

#### B. ビジネスロジック攻撃（ログインジェクション / CRLF 偽造）

```
B1 {"level":"INFO","message":"ok\nCRITICAL fake breach"}
B2 {"level":"INFO","message":"ok\rERROR injected"}
B3 {"message":"a\r\nb"}  (/structured)
```
**結果**: すべて **200** だが改行はリテラル化。`INFO ok\nCRITICAL fake breach` / `INFO ok\rERROR injected` のように `\n` `\r` が 2 文字へエスケープされ、**偽ログ行の注入は不成立**。JSON 構造化ログでも `message` 値内にエスケープ済みで封じ込め。

#### C. フォーマット文字列インジェクション

```
C1 {"level":"INFO","message":"%s%s%s"}
C2 {"level":"INFO","message":"%(asctime)s %(__class__)s"}
C3 {"level":"INFO","message":"%d %x"}
```
**結果**: すべて **200** でリテラル出力（`INFO %s%s%s` 等）。`logger.log(level, "%s", safe)` の遅延フォーマットにより、ユーザー入力は書式文字列にならず、`TypeError` も `LogRecord` 属性の漏洩も発生せず。

#### D. 情報収集攻撃（秘匿バイパス）

```
D1 {"message":"PASSWORD=Secret123"}        # 大文字
D2 {"message":"token  =  leaktoken"}       # 空白入り
D3 {"message":"{\"api_key\":\"abc\"}"}     # JSON 埋め込み
D4 {"message":"password=a token=b secret=c"}  # 複数
```
**結果**: D1/D2/D4 は **秘匿成功**（`PASSWORD=***REDACTED***` / `token  =  ***REDACTED***` / 3 件すべて置換）。大文字小文字非依存・空白許容・複数マッチに対応。**D3 のみ秘匿されず**（`{"api_key":"abc"}` がそのまま）→ 下記「発見した弱点」参照。

#### E. DoS 試み

```
E1 message = "x"*501                       # 上限 +1
E2 message = "x"*500                        # 上限ちょうど
E3 redact: "password=" + "a"*450           # 秘匿正規表現の ReDoS 探索
E4 redact: "password="*55                   # キー反復
```
**結果**: E1 は **422**（Pydantic `max_length=500`）、E2 は **200**。E3/E4 とも **200 を 2.6ms / 3.3ms** で応答 — 秘匿正規表現は線形時間で **ReDoS なし**（バックトラッキング爆発を起こすネスト量化子を持たない）。

### フェーズ3: 攻撃まとめ

| 攻撃カテゴリ | 試みた攻撃数 | 突破 | 耐えた | 予期しない動作 |
|---|---|---|---|---|
| Pydantic バイパス | 4 | 0 | 4 | 0 |
| ログインジェクション(CRLF) | 3 | 0 | 3 | 0 |
| フォーマット文字列注入 | 3 | 0 | 3 | 0 |
| 情報収集(秘匿) | 4 | 0 | 3 | 1（D3 軽微） |
| DoS | 4 | 0 | 4 | 0 |

**攻撃耐性評価**: 軽微な問題あり（秘匿は多層防御の補助であり主防御ではない）
**発見した弱点**:

- **D3（LOW）**: `_RedactingFilter` の正規表現は `key=value` / `key: value` 形のみを対象とするため、JSON 埋め込みの `"api_key":"abc"`（キーとセパレータの間に `"` が挟まる形）は秘匿されない。
  - **評価**: redaction は「うっかり機密が混ざったときの**多層防御の保険**」であり、第一の防御は **そもそも機密をログに渡さないこと**（CLAUDE.md: `SecretStr` 運用）。本 FT のデモスコープでは許容するが、本番で JSON ペイロードをログに残す要件があるなら、構造化フィールド単位での秘匿（`logging.LoggerAdapter` / `extra` のキーホワイトリスト）に切り替えるべき。Follow-up として「秘匿は形式に依存する best-effort であり主防御にしない」旨を how-to に明記する。

---

## テスト結果

```
11 passed in 0.30s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`print()` の代わりに `logging` を使うことは知っていても、Logger → Filter → Formatter → Handler のパイプラインは初見では複雑に感じる。「メッセージを送ると整形済みログ行が返る」という API なら全体像はつかめる。

**ドキュメント理解**: `_capturing()` の attach/detach や `propagate=False` の意味は最初わからない。コメントが理由まで書いてあるので追える。
**事故リスク（高）**: `logger.info(user_input)` をそのまま書いてしまう典型ミスをしやすい。フォーマット文字列インジェクションの存在自体を知らない。
**規約の使いやすさ**: `level` を文字列で送る形式は直感的。422 が返るので不正入力に気付ける。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

社内バッチのログを API 経由で見せる、といったユースケースは実務で出会う。`_RedactingFilter` はコピペで自社ログに転用したくなる。

**コピペ可能性**: `_capturing()` contextmanager はそのまま流用できる完成度。
**拡張時の罠**: `getLogger()` 由来の Logger に `addHandler()` しっぱなしにすると本番でログが N 重化する。`try/finally` での detach を省略しがち。
**事故リスク（中）**: 秘匿正規表現を「完璧な防御」と誤認してログに機密を流し込む危険（D3）。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`console.log` の感覚に近いが、Python の `%` スタイル遅延フォーマットは JS のテンプレートリテラルと違って戸惑う。

**エラーレスポンスの質**: 不正レベルや超過長は 422 Problem Details で `{field, message, code}` が返り、フロントで扱いやすい。
**Python 固有概念の学習コスト**: `logger.info("%s", x)` の「引数で渡す」理由（インジェクション回避＋遅延評価）は Python 特有で学習コストがある。
**事故リスク（低）**: 入力は Pydantic で長さ制限済み。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `LOGGING` 設定や `structlog` を使ってきた身からすると、`_JsonFormatter` は構造化ログの最小実装として妥当。

**他フレームワークとの差異**: `structlog` や `python-json-logger` はフォーマット文字列インジェクションや CRLF を内部で処理してくれるが、標準 `logging` を直接使うなら `_sanitize()` 相当を自前で持つ必要がある。本 FT はその「素の logging を安全に使う型」を示せている。
**nene2 の薄さへの評価**: ロギングは本来アプリ横断の関心事。HTTP でラップする薄い層として例示は適切だが、本番では nene2 の `nene2.log`（structlog セットアップ）を使うべき。
**事故リスク（低）**: ペンテスト合格、ReDoS なし。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `logger.xxx(user_input)` を直接渡していないか — フォーマット文字列インジェクションの最頻出ミス。必ず `("%s", value)` 形か確認。
- ログメッセージに改行サニタイズが入っているか — 監査ログ偽造（CRLF）防止。
- `getLogger()` に `addHandler()` した後 `removeHandler()` しているか — ハンドラ蓄積によるログ N 重化・メモリリーク。
- `propagate` を制御しているか — ルートロガーへの意図しない伝播。
- 秘匿 Filter を「主防御」として扱っていないか — `SecretStr` 等で**そもそもログに出さない**のが第一。

**チームでの安全なパターン**: `_capturing()` と `_sanitize()` を共通モジュールに切り出し、ロギング箇所で強制的に経由させる。
**事故リスク（低）**: 設計上の罠（F-1〜F-3）が明示され、テストで回帰防止済み。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 入力検証（`max_length`）・`frozen=True, slots=True` dataclass・`ValidationException` 変換・`print()` 不使用（`logging` のみ）はすべて準拠。フォーマット文字列を遅延引数で渡す点は「ログには `logging` モジュールのみ使用」ポリシーの正しい運用例。
**初心者でも安全な API 達成度**: `logger.info(user_input)` の罠を `_sanitize()` ＋ `("%s", ...)` 経由でフレームワーク的に封じた点は良い。ただし秘匿 Filter の形式依存（D3）は「保険であって主防御でない」と明記が必要。
**改善提案**:
- `_capturing()` / `_sanitize()` は `nene2.log` に「安全なリクエストスコープロギング」ユーティリティとして昇格する価値がある。
- how-to に「ログに機密を出さない（`SecretStr`）＋ 秘匿 Filter は多層防御の保険」を 1 本追加する。
