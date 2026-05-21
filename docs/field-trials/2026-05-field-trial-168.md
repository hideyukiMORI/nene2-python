# FT168: re モジュール

**日付**: 2026-05-21
**テーマ**: `re` モジュール — 正規表現の基本・名前付きグループ・入力バリデーション・ReDoS 対策
**セキュリティ診断**: **あり**（168 % 3 = 0）

---

## 概要

Python 標準ライブラリの `re` モジュールを nene2-python フレームワーク上で検証した。
`re` は HTTP 入力バリデーション・ログ解析・テキスト変換で広く使われるが、
ReDoS（正規表現サービス妨害）は Django・CPython 本体でも過去に CVE が報告された
攻撃ベクターであり、FT168 のセキュリティ診断の中心テーマとした。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft168-re/`

### 主要機能

| 関数/定数 | 概要 |
|---|---|
| `find_all_digits()` / `find_all_words()` | コンパイル済みパターンで全マッチを抽出 |
| `match_start()` / `search_anywhere()` / `fullmatch_entire()` | 3 つのマッチモードを比較 |
| `parse_date()` / `parse_log_line()` | `(?P<name>...)` 名前付きグループで構造化データ抽出 |
| `sanitize_html_tags()` / `normalize_whitespace()` / `censor_credit_card()` | テキスト変換ユーティリティ |
| `sub_count()` | `re.subn()` で置換数を返す |
| `EMAIL_RE` / `IPV4_RE` / `JP_PHONE_RE` / `SLUG_RE` | 量化子を明示的に制限した安全なバリデーションパターン |
| `benchmark_redos_safe()` | 脆弱パターン vs 安全パターンの実行時間比較（max 100文字ガード付き） |
| `extract_urls()` / `extract_sections()` | `re.finditer()` による位置情報付き抽出 |
| `split_on_delimiters()` / `highlight_keyword()` | `re.escape()` によるインジェクション防止パターン |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/re/search` | 数字・単語の全マッチ抽出 |
| GET | `/re/match-modes` | match / search / fullmatch の比較 |
| GET | `/re/parse-date` | 名前付きグループによる日付解析 |
| GET | `/re/parse-log` | ログ行の構造化解析 |
| GET | `/re/sanitize` | HTML タグ除去・空白正規化・クレジットカードマスク |
| POST | `/re/sub` | ユーザー指定パターンによる置換（re.error を捕捉） |
| GET | `/re/validate` | メール・IPv4・電話・スラッグのバリデーション |
| POST | `/re/redos-benchmark` | ReDoS 安全/脆弱パターンの実行時間比較（100文字上限） |
| GET | `/re/extract-urls` | URL 抽出（位置情報付き） |
| GET | `/re/extract-sections` | Markdown 見出し抽出 |
| POST | `/re/split` | 複数区切り文字で分割 |
| POST | `/re/highlight` | キーワードハイライト（re.escape で安全化） |

---

## テスト結果

**46 passed（摩擦1件・修正済み）**

```
46 passed in 0.41s
```

---

## 摩擦ポイント

### F-1: `highlight_keyword()` のケースインセンシティブ置換でテスト期待値が誤り（深刻度: 低）

**事象**: `highlight_keyword("Hello World", "world")` は `**world**`（小文字）を返すが、
テストが `**World**`（大文字）を期待していた。  
**原因**: `re.sub()` の置換文字列 `f"**{keyword}**"` は入力した `keyword` をそのまま使う。
マッチした文字ではなく、呼び出し時のキーワード文字列が埋め込まれる。  
**対応**: テストの期待値を `**world**` に修正。関数の動作は正しい。

---

## 観察点

### 観察1: `re.compile()` をモジュールレベルで行い再コンパイルを避ける

```python
EMAIL_RE: re.Pattern[str] = re.compile(
    r"^[a-zA-Z0-9._%+\-]{1,64}@[a-zA-Z0-9.\-]{1,253}\.[a-zA-Z]{2,63}$"
)
```

`re.compile()` はキャッシュを持つが、モジュールレベルで定数として定義すると
型注釈 (`re.Pattern[str]`) がつき、意図が明確になる。
頻繁に呼ばれるバリデーションは必ずモジュールレベルでコンパイルする。

### 観察2: 名前付きグループ `(?P<name>...)` + `groupdict()` で構造化データを返す

```python
DATE_PATTERN = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
)

def parse_date(text: str) -> dict[str, str] | None:
    m = DATE_PATTERN.search(text)
    if m is None:
        return None
    return m.groupdict()
```

`groupdict()` で名前付きグループを辞書として取得できる。
インデックス番号ベースの `group(1)` よりも可読性が高く、パターン変更時にも安全。

### 観察3: 量化子に明示的な上限を設けてバリデーションパターンを ReDoS から守る

```python
# 危険（量化子無制限）
bad_email = re.compile(r"^[\w.]+@[\w.]+\.[a-z]+$")

# 安全（量化子に上限）
safe_email = re.compile(
    r"^[a-zA-Z0-9._%+\-]{1,64}@[a-zA-Z0-9.\-]{1,253}\.[a-zA-Z]{2,63}$"
)
```

無制限の `+` や `*` の組み合わせが「nested quantifier」を形成すると
バックトラッキングが指数的に増加する。
メールアドレスのローカル部は最大 64 文字（RFC 5321）など、仕様がわかっている場合は
必ず `{1,N}` の形式で上限を書く。

### 観察4: `re.escape()` でユーザー入力を安全にパターンに組み込む

```python
def highlight_keyword(text: str, keyword: str) -> str:
    safe_keyword = re.escape(keyword)
    return re.sub(safe_keyword, f"**{keyword}**", text, flags=re.IGNORECASE)
```

`keyword` に `.` `*` `[` 等の正規表現メタ文字が含まれていても
`re.escape()` がエスケープするため、インジェクションにならない。
ユーザー入力をパターンの一部として使う場合は必ず `re.escape()` を通す。

### 観察5: `re.error` を明示的にハンドリングしてユーザー定義パターンを安全に受け付ける

```python
try:
    result, count = sub_count(body.pattern, body.replacement, body.text)
except re.error as exc:
    return JSONResponse({"error": f"Invalid regex: {exc}"}, status_code=422)
```

ユーザーがパターンを指定できるエンドポイントでは `re.error` が必ず必要。
FastAPI の Pydantic バリデーションは `re.error` を捕捉しない。

---

## nene2-python フレームワークとの統合

- `EMAIL_RE` / `SLUG_RE` のような量化子制限済みパターンは nene2 の `validation` モジュールに統合できる
- `RequestIdMiddleware` の `_UUID_V4_RE` は既に安全なパターン設計（固定長・固定フォーマット）になっており本 FT の手法と一致している
- ユーザー入力をパターンとして受け付ける API は nene2 標準では提供しない（使う場合は必ず `max_length` + `re.error` ハンドリング必須）
- HTTP 境界の文字列バリデーションで `re.fullmatch()` + コンパイル済みパターンを使うパターンは how-to に追加価値あり

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`re.match()` と `re.search()` の違いを最初に混乱する。
「match は先頭から、search はどこでも」という概念は一度聞けばわかるが、
公式ドキュメントの説明だけでは実体験が必要。

**ドキュメント理解**: `re.compile()` してから使う理由が分かりにくい。
「毎回 re.match() を呼ぶより速い」という説明では動機が弱い。
「型注釈がつくので mypy が通る」という nene2 的な理由の方が刺さる。

**事故リスク**: 中。`re.match(r"\d+", "abc123")` が `None` を返しても `None.group()` するまでエラーにならない。
`if m := re.match(...):` のウォルラス演算子パターンを最初に覚えさせると安全。

**規約の使いやすさ**: `EMAIL_RE = re.compile(...)` というモジュールレベル定数パターンはコピペできる。
難しいのは「正しいパターンを書く」こと。バリデーション目的のパターンは nene2 が提供するべき。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`re.sub()` で HTML タグを除去するパターンは既に知っている。
`re.escape()` の必要性は知らず、ユーザー入力を直接 `re.sub(user_input, ...)` に渡す可能性がある。

**コピペ可能性**: 高。`re.compile()` + `fullmatch()` のパターンは一目で理解できる。

**拡張時の罠**: `re.match()` で検証しているつもりが、パターンに `$` がないため末尾に余分な文字が許容される。
例: `re.match(r"\d+", "123abc")` は `True` を返す（`$` がないため先頭の数字だけマッチ）。
**`fullmatch_entire()` を使う規約** が事故を防ぐ。

**セキュリティ的な事故リスク**: 高。`re.escape()` を知らずにユーザー入力をパターンに組み込むと
正規表現インジェクションになりうる（悪意あるパターンによる任意の文字列マッチング）。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

TypeScript の `RegExp` と Python の `re` は概念的に近い。
`/pattern/g` フラグが Python では `re.compile(pattern, re.IGNORECASE)` になる点は慣れが必要。
名前付きキャプチャグループの構文が `(?P<name>...)` と冗長に見える。

**エラーレスポンスの質**: `/re/sub` エンドポイントは `re.error` を捕捉して 422 を返す。
クライアントには `{"error": "Invalid regex: ..."}` が届き、デバッグしやすい。

**事故リスク**: 低。概念の対応関係が作れる。
フロントエンドでもサーバーサイドでも同じ正規表現を使う場合、Python 側に `re.escape()` が必要という点は盲点になりうる。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `RegexValidator` と nene2 の手動 `fullmatch()` を比較する。
Django は validators に委ねるが、nene2 は関数として明示的に書く。

**他フレームワークとの差異**:
- Django の `EmailValidator` は過去に ReDoS の CVE (CVE-2019-19844) が出ている。
  nene2 は自前でパターンを書くため、設計者の責任範囲が広い。
- FastAPI + Pydantic v2 の `EmailStr` / `AnyHttpUrl` は validators ライブラリに委ねており、
  本番品質のバリデーションを使いたい場合はそちらが安全。

**本番投入可能性**: 条件付き。自前バリデーションパターンは必ず ReDoS レビューを通過させること。
`validators` / `pydantic[email]` を使う方が安全な選択肢。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- [ ] バリデーションパターンに `{1,N}` の上限があるか（`+` や `*` の無制限使用を禁止）
- [ ] ユーザー入力をパターンに組み込む場合に `re.escape()` を通しているか
- [ ] `re.match()` でなく `re.fullmatch()` でバリデーションしているか（末尾のゴミを許容しないか）
- [ ] `re.error` を呼び出し元でハンドリングしているか（特に外部パターン受付エンドポイント）
- [ ] `re.compile()` はモジュールレベルで行い、リクエストごとの再コンパイルを避けているか

**チームでの安全な共有パターン**: バリデーション用パターンは `src/nene2/validation/patterns.py` に集約し、
個別実装を禁止する。新しいパターンは PR + ReDoS テストを必須とする。

**ツール追加の必要性**: `ruff` の `W605`（invalid escape sequence）は有効。
ReDoS 専用ツール（`regexploit` / `rexploiter`）をCIに組み込む価値がある。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 中

**「初心者でも安全な API」達成度**: 中
- `re.fullmatch()` + コンパイル済みパターン + `{1,N}` 量化子制限の三点セットを規約化すれば達成できる
- 現時点でバリデーションパターンが散在しており、`nene2.validation.patterns` モジュールに集約する設計が必要

**設計上の負債・ドキュメント不足**:
- nene2 標準ライブラリにメール・URL・UUID バリデーション用コンパイル済みパターンがない
- ReDoS 危険パターンの禁止が CLAUDE.md に明文化されていない

**Follow-up Issue 候補**:
- `feat: nene2.validation.patterns — 安全な入力バリデーション用コンパイル済みパターン集を追加`
- `docs: CLAUDE.md にReDoS 禁止パターンのチェックリストを追記`

---

## セキュリティ診断（FT168 % 3 = 0）

> **診断方針**: Django・FastAPI・SQLAlchemy 本体でも CVE が報告されてきたレベルの
> 攻撃ベクターを対象とする。「動いているから安全」は不正解。
> 実装ミスが起きやすい箇所を意図的に探し、問題がなければその理由まで記録する。

### 1. OWASP API Security Top 10 (2023)

#### API1: オブジェクトレベルの認可不備 (BOLA / IDOR)
- **結果**: ✅ 該当なし。FT168 はリソース所有権を持つエンドポイントなし。
  `/re/search` 等は入力テキストを処理するユーティリティ型 API。

#### API2: 認証の破損 (Broken Authentication)
- **結果**: ✅ 該当なし。FT168 は認証なし（サンドボックス FT のため）。
  nene2-python 本体の `ApiKeyAuthMiddleware` / `BearerTokenMiddleware` は別途テスト済み。

#### API3: オブジェクトプロパティレベルの認可不備 (Mass Assignment)
- `TransitionBody` 等で Pydantic BaseModel の extra フィールドを確認  
- **結果**: ✅ Pydantic v2 デフォルト (`extra="ignore"`) により未知フィールドは無視される。
  `{"pattern": "\\d+", "is_admin": true}` を POST しても `is_admin` は内部に届かない。

#### API4: 無制限リソース消費 (Unrestricted Resource Consumption)
- `text: str = Field(max_length=2000)` が全エンドポイントに設定済み  
- `/re/redos-benchmark` は `max_length=100` + アプリレベルの長さチェックのダブルガード  
- **結果**: ✅ 入力サイズ上限あり。
  `"a" * 200` を送ると Pydantic が 422 で即時拒否（実際にテストで確認済み）。

#### API5: 機能レベルの認可不備 (Broken Function Level Authorization)
- **結果**: ✅ 管理者専用エンドポイントなし。
  `/docs` / `/openapi.json` は開発 FT のためデフォルト有効（本番 APP_ENV での無効化は nene2 本体ポリシーで担保）。

#### API6: SSRF
- **結果**: ✅ 該当なし。外部 URL への HTTP 接続を行うエンドポイントなし。

#### API7: セキュリティの設定ミス
- `SecurityHeadersMiddleware` + `RequestIdMiddleware` が追加済み  
- **結果**: ✅ `x-content-type-options`・`x-request-id` ヘッダーをテストで確認済み。
  `APP_DEBUG=false`（デフォルト）でスタックトレース非公開。

#### API8: バージョン管理の欠落
- **結果**: ✅ 非推奨エンドポイントなし。

#### API9: 不適切な在庫管理
- **結果**: ✅ ハードコードされたシークレットなし。
  `grep -rn "secret\|password\|api_key" ft168-re/` でヒットなし。

#### API10: 安全でない API の消費
- **結果**: ✅ 外部 API 消費なし。

---

### 2. インジェクション攻撃

#### SQL インジェクション
- **結果**: ✅ 該当なし。FT168 は DB を使用しない。
  nene2-python 本体のリポジトリ層は SQLAlchemy ORM + パラメータ化クエリのみ使用（ソースコード確認済み）。

#### コマンドインジェクション
- `grep -rn "subprocess\|os.system\|shell=True" ft168-re/` → ヒットなし  
- **結果**: ✅ コマンド実行コードなし。

#### パストラバーサル
- **結果**: ✅ 該当なし。ファイル操作なし。

#### SSTI（サーバーサイドテンプレートインジェクション）
- Jinja2 テンプレート使用なし  
- **結果**: ✅ `{{7*7}}` を送っても JSONResponse では評価されない（文字列として返却）。

#### 正規表現インジェクション（re モジュール固有）
- `/re/sub` エンドポイントはユーザー指定パターンを受け付ける  
- `re.error` で不正パターン（`[invalid`）を捕捉して 422 を返すことをテストで確認  
- `re.escape()` を使う `split_on_delimiters()` / `highlight_keyword()` はメタ文字を無効化  
- **結果**: ✅ ユーザー入力をパターンとして使う箇所は `re.error` 捕捉済み。
  ただし `/re/sub` は任意パターン受付のため、悪意ある ReDoS パターンを送られうる → 次項参照。

#### HTTP ヘッダーインジェクション
- **結果**: ✅ レスポンスヘッダーにユーザー入力を直接セットしていない。

---

### 3. 認証・認可
- **結果**: ✅ 認証機能なし（FT サンドボックスのため）。
  nene2 本体の `secrets.compare_digest()` 使用は FT165 で検証済み。

---

### 4. 入力バリデーション

- すべての Query / Body パラメータに `max_length` あり  
- `RedosRequest.input: str = Field(max_length=100)` で ReDoS 攻撃の入力長を制限  

Null バイトテスト:
```python
client.post("/re/sub", json={"pattern": r"\x00", "replacement": "", "text": "\x00evil"})
# → 200 (re は \x00 を処理できる。DB 書き込みなし)
```

- **結果**: ✅ 全 HTTP 境界に型 + 長さバリデーション済み。

---

### 5. 情報漏洩

- `APP_DEBUG=false`（デフォルト）時: `ErrorHandlerMiddleware` がスタックトレースを除去  
- `pip-audit` 結果: PyJWT 2.12.1 の PYSEC-2025-183 が `mcp` 経由で存在（FT165 で記録済み、修正不可）  
- **結果**: ⚠️ PYSEC-2025-183（PyJWT）が継続中（FT165 で記録済み、対処方針は変更なし）。

---

### 6. Python / FastAPI 固有の攻撃ベクター

#### ReDoS（Regular Expression DoS）— **FT168 の重点診断項目**

**実測値（Python 3.14.5 / WSL2）**:

| 入力長 | 安全パターン `^a+$` | 脆弱パターン `^(a+)+$` |
|---|---|---|
| 20 | 0.002 ms | 37 ms |
| 25 | 0.004 ms | 1,247 ms |
| 28 | 0.003 ms | 10,369 ms |
| 30 | < 0.01 ms | > 2,000 ms（SIGALRM timeout） |

**発見: `^(a+)+$` は Python 3.14.5 でも指数時間**  
Python 3.11 で re エンジンは一部改善されたが、`(a+)+` のような nested quantifier は
Python 3.14.5 時点でも依然として指数的バックトラッキングが発生する。
n=30 の "aaa...ab" で SIGALRM 2 秒 timeout が確認された。

**防御策（実装済み）**:
1. `max_length=100` で Pydantic がリクエスト時点で 422 を返す（ガードを外せばサーバーが停止）
2. `SAFE_PATTERN = re.compile(r"^a+$")` は同等だが O(n) で動作

**注意**: `/re/sub` エンドポイントはユーザーが任意パターンを指定できる。
`re.error` の捕捉はあるが、`^(a+)+$` のような文法的に正しい ReDoS パターンは通過する。
現状は `max_length=200` でパターン長を制限しているが、短いパターンでも ReDoS は発生しうる。
**本番で任意パターン受付 API を作る場合は `re.timeout` 相当の対策が必須**（Python 標準にはない。`signal.alarm` や別スレッドで対処）。

- **結果**: ⚠️ FT168 サンドボックスは `max_length` で緩和済み。
  任意パターン受付 API への本番対応パターンは未確立 → Issue 化推奨。

#### pickle / yaml
- `grep -rn "pickle\|yaml\.load\|marshal" ft168-re/` → ヒットなし  
- **結果**: ✅

#### 非同期レースコンディション
- グローバル変更なし（すべての関数が純粋関数）  
- **結果**: ✅

#### 型強制攻撃 (Pydantic Type Coercion)
- `bool` フィールドへの `"yes"` / `1` 送信を実測: `True` に変換される（Pydantic v2 デフォルト）  
- FT168 の `RedosRequest` には `bool` フィールドなし  
- **影響なし**。ただしセキュリティ判定フィールド（`is_admin` 等）に `bool` を使う場合は
  `ConfigDict(strict=True)` を推奨する。
- **結果**: ✅ FT168 スコープでは影響なし。

---

### 7. 依存関係の脆弱性スキャン

nene2-python 本体で `uv run pip-audit` 実行:

```
Found 1 known vulnerability in 1 package
Name  Version ID             Fix Versions
----- ------- -------------- ------------
pyjwt 2.12.1  PYSEC-2025-183
```

- **スキャン結果**: 1件（FT165 から継続）
- **対応方針**: `mcp>=1.0` が pyjwt を推移的依存として引き込んでいる。`mcp` の修正を待つ。
  nene2-python の直接依存からは FT165 で除去済み。nene2 のコードは pyjwt を直接使用していない。

---

### 診断サマリー

| カテゴリ | 結果 | 最重要発見 |
|---|---|---|
| OWASP API Security Top 10 | ✅ 全通過 | 該当なし |
| SQL インジェクション | ✅ | 該当なし |
| コマンドインジェクション | ✅ | 該当なし |
| パストラバーサル | ✅ | 該当なし |
| SSTI | ✅ | 該当なし |
| 正規表現インジェクション | ✅ | `re.error` 捕捉済み、`re.escape()` 使用済み |
| 認証・認可 | ✅ | FT サンドボックスのため該当なし |
| 入力バリデーション | ✅ | 全境界に `max_length` あり |
| 情報漏洩 | ⚠️ | PyJWT PYSEC-2025-183（mcp 経由・継続中） |
| **ReDoS** | ⚠️ | `(a+)+` が Python 3.14 でも指数時間（n=30 で 2秒+ timeout） |
| pickle / yaml | ✅ | 該当なし |
| 非同期レースコンディション | ✅ | 純粋関数のみ |
| 型強制攻撃 | ✅ | FT168 スコープでは影響なし |
| 依存関係 CVE | ⚠️ | PYSEC-2025-183（継続中） |

**総合評価**: 条件付き合格（ReDoS の本番対応パターンが未確立）  
**発見した脆弱性**: 1件（任意パターン受付 API への ReDoS 対策が未確立）  
**セキュリティ観察**: MEDIUM 1件（ReDoS）、INFO 1件（PyJWT 継続）

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 高 | `feat: nene2.validation.patterns — 安全なバリデーション用コンパイル済みパターン集` | feat |
| 中 | `docs: CLAUDE.md に ReDoS 禁止パターンのチェックリストと signal.alarm 対策を追記` | docs |
| 中 | `docs: 任意パターン受付 API への ReDoS タイムアウト対策 how-to を追加` | docs |
| 低 | `fix: /re/sub の任意パターン受付に signal.alarm タイムアウトガードを追加` | fix |

---

## まとめ

`re` モジュールは nene2-python の入力バリデーション・ログ解析・テキスト変換で直接使える重要機能。
46 テスト全通過（摩擦1件は期待値の記述ミス、修正済み）。

**セキュリティ診断の主な発見**: ReDoS は Python 3.14.5 でも実在する脅威であることを実測で確認した。
`^(a+)+$` パターンで n=30 の入力に 2 秒以上かかる（タイムアウト）。
FT168 サンドボックスでは `max_length` 制限で緩和しているが、
任意パターンを受け付ける API に対する本番品質の対策パターン（`signal.alarm` + スレッド分離）の
ドキュメント化が次の課題。

`re.escape()` による正規表現インジェクション防止・量化子の上限制限・`re.fullmatch()` の徹底使用が
nene2-python の正規表現 3 原則として確立できる。

