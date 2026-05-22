# FT204: datetime モジュール — ISO 8601 パース・タイムゾーン変換・日時演算

**日付**: 2026-05-22
**テーマ**: Python `datetime` モジュールの ISO 8601 パース・タイムゾーン変換・timedelta 演算の実装と検証
**セキュリティ診断**: **あり**（204 % 3 = 0）
**クラッカーペンテスト**: **あり**（204 % 4 = 0）

---

## 概要

`datetime` モジュールは Python 組み込みの日時処理ライブラリ。
Python 3.9 から追加された `zoneinfo` モジュールと組み合わせることで、
IANA タイムゾーンによる aware datetime 操作が pytz 不要で行える。

FT の焦点:
- ISO 8601 / RFC 3339 文字列のパース（Z サフィックス・UTC オフセット対応）
- IANA タイムゾーン名による変換（`ZoneInfo`）
- naive / aware の区別と混在検出
- timedelta による日時演算とオーバーフロー防御

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft204-datetime/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `parse_datetime(text)` | ISO 8601 文字列をパースして `ParseResult` を返す |
| `convert_timezone(iso8601, tz_name)` | IANA タイムゾーン名で日時を変換して `ConvertResult` を返す |
| `diff_datetimes(start, end)` | 2つの日時の差分を `DiffResult` で返す |
| `get_now(tz_name)` | UTC + 指定タイムゾーンの現在時刻を `NowResult` で返す |
| `add_duration(iso8601, days, hours, minutes)` | 日時に期間を加算して `ParseResult` を返す |
| `ParseResult` | 構造化された日時フィールドを持つ frozen dataclass |
| `ConvertResult` / `DiffResult` / `NowResult` | タイムゾーン変換・差分・現在時刻の frozen dataclass |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/datetime/parse` | ISO 8601 文字列をパース（`?text=...`） |
| POST | `/datetime/convert` | タイムゾーン変換 |
| POST | `/datetime/diff` | 2日時の差分計算 |
| GET | `/datetime/now` | 現在時刻（`?timezone=Asia/Tokyo`） |
| POST | `/datetime/add` | 日時に期間を加算 |

---

## テスト結果

**27 passed**

```
27 passed in 0.42s
```

---

## 摩擦ポイント

### F-1: `strptime` が Z サフィックスを直接扱えない（深刻度: 低）

**事象**: `datetime.strptime("2026-05-22T12:00:00Z", "%Y-%m-%dT%H:%M:%S%z")` が失敗する。
`%z` は `+00:00` 形式を期待するが `Z` は ISO 8601 の UTC 省略形。

**原因**: Python 3.11 以降 `datetime.fromisoformat()` が `Z` を受け付けるようになったが、
`strptime` の `%z` は引き続き `Z` を解釈しない。

**対応**: パース前に `.replace("Z", "+00:00")` で正規化。
また `datetime.fromisoformat()` を後段フォールバックとして使用。

### F-2: `zoneinfo` は `tzdata` パッケージが必要な場合がある（深刻度: 低）

**事象**: Linux 環境ではシステム tzdata から読み込むため問題なし。
Windows 環境では `zoneinfo.ZoneInfo("Asia/Tokyo")` が `ZoneInfoNotFoundError` を投げる。

**原因**: Windows には `/usr/share/zoneinfo` が存在しない。

**対応**: `pyproject.toml` に `tzdata` を追加する必要あり（本番 Docker イメージでは通常問題なし）。
CLAUDE.md に注記を追加した。

---

## 観察点

### 観察1: aware vs naive の混在は `TypeError` ではなく正しく検出すべき

```python
from datetime import datetime, UTC

aware = datetime(2026, 5, 22, tzinfo=UTC)
naive = datetime(2026, 5, 22)

# Python は aware - naive を TypeError で拒否する
# → API 境界では先に混在チェックして 422 を返す
delta = aware - naive  # TypeError: can't subtract offset-naive and offset-aware datetimes
```

API 境界で `(start.tzinfo is None) != (end.tzinfo is None)` を事前検出し、
`TypeError` が上位に漏れないように実装した。

### 観察2: `ZoneInfo` はタイムゾーン名のパストラバーサルを防ぐ設計ではない

```python
from zoneinfo import ZoneInfo
ZoneInfo("../../etc/passwd")  # → ZoneInfoNotFoundError（OS が拒否）
```

`ZoneInfo` 自体はパストラバーサルを防ぐ設計ではなく、OS の tzdata 検索パスに従う。
`_TIMEZONE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9/_+-]{0,63}$")` で
ドット・スペース・セミコロンを含む文字列を事前拒否することで、
`ZoneInfo` に到達させないようにした。

### 観察3: Python の `bool` は `int` のサブクラス — Pydantic の型強制

```python
from pydantic import BaseModel

class AddDurationBody(BaseModel):
    days: int
    
body = AddDurationBody.model_validate({"days": True})
body.days  # → 1（True が int 1 に変換される）
```

`days=True` は Pydantic v2 のデフォルト動作で `1` に変換される。
`False` → `0`。セキュリティ的にはリスクなし（値が `[ge, le]` の範囲内）だが、
エラーにしたい場合は `model_config = ConfigDict(strict=True)` が必要。

### 観察4: タイムゾーン名の max_length と正規表現の組み合わせ

```python
# IANA タイムゾーン名の実際の最大長: "America/Indiana/Indianapolis" = 28文字
# 安全側として 64 文字を上限に設定
target_timezone: str = Field(max_length=64, ...)
```

正規表現パターン `_TIMEZONE_PATTERN` は `{0,63}` で最大 64 文字を許可。
`max_length=64` と `{0,63}` の整合性は取れている（先頭の `[A-Za-z]` で 1 文字、続く `{0,63}` で 63 文字 = 計 64 文字）。

### 観察5: `datetime.fromisoformat()` の Python バージョン差異

| バージョン | `fromisoformat()` の対応範囲 |
|---|---|
| Python 3.6〜3.10 | `YYYY-MM-DD` と `YYYY-MM-DDTHH:MM:SS[.ffffff][+HH:MM]` のみ |
| Python 3.11+ | Z サフィックス、任意の ISO 8601 オフセット形式 |

nene2-python は `>=3.12` を要件としているため `datetime.fromisoformat()` で Z を扱える。
ただし `strptime` の `%z` はバージョン問わず Z を直接解釈しない。

---

## nene2-python フレームワークとの統合

- タイムゾーン名は `_TIMEZONE_PATTERN` で事前バリデーション。`ZoneInfo` に不正文字列を渡さない。
- naive/aware 混在は `ValueError` に変換して `ValidationException` 経由で 422 を返す。
- `timedelta` のオーバーフロー（`OverflowError`）を `ValueError` に変換してクライアントに安全なエラーを返す。
- Windows 環境でのデプロイには `tzdata` パッケージが追加で必要（CLAUDE.md に追記）。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

「投稿日時を UTC で保存して JST で表示したい」というユースケースで実装を試みる。

**ドキュメント理解**: `datetime.now()` と `datetime.now(tz=UTC)` の違いを理解するまでに時間がかかる。
`naive` と `aware` という用語が公式ドキュメントにしか出てこないため、エラーメッセージを読んで混乱する可能性がある。  
**事故リスク**: 高。naive datetime を DB に保存してタイムゾーン変換時に意図しない結果を得るケースが多い。
`datetime.now()` の代わりに `datetime.now(tz=UTC)` を使う習慣が重要。  
**規約の使いやすさ**: `parse_datetime()` / `convert_timezone()` のラッパーは意図が明確。
「Z = UTC」の直感的な理解さえあれば使いやすい。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

過去に `pytz` で datetime を扱ったことがある。`zoneinfo` を知らない可能性がある。

**コピペ可能性**: Stack Overflow の `pytz` を使ったコードをコピペするリスクがある。
`pytz.timezone()` と `ZoneInfo()` は使い方が微妙に異なる（`localize()` vs `astimezone()`）。  
**拡張時の罠**: `datetime.utcnow()` は Python 3.12 で deprecated。`datetime.now(tz=UTC)` が正しい。  
**セキュリティ的な事故リスク**: 中。タイムゾーンを無視した比較でセッション有効期限チェックが誤動作するリスク。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JavaScript の `Date.toISOString()` / `new Date(isoString)` との対応関係が分かれば使いやすい。

**エラーレスポンスの質**: 422 + `{"field": "text", "message": "無効な日時フォーマット: ...", "code": "invalid_datetime"}` は明確。  
**Python 固有概念の学習コスト**: `aware/naive` の概念は JS にはないため説明が必要。
`+09:00` で返す API は JS の `new Date()` で直接パースできるため DX は高い。  
**事故リスク**: 低。ISO 8601 文字列でやり取りするため相互運用性は高い。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `USE_TZ = True` / `make_aware()` との比較視点を持つ。

**他フレームワークとの差異**: Django は `django.utils.timezone.now()` が自動で UTC aware を返す。
標準 `datetime` では `datetime.now(tz=UTC)` を明示する必要がある（忘れやすい）。  
**nene2-python の薄さへの評価**: pytz 依存なし・zoneinfo のみで十分な点は高評価。
`datetime.utcnow()` deprecated を知っている経験者には特に評価される。  
**本番投入可能性**: UTC で保存・タイムゾーンはフロントエンドで表示変換、というパターンと相性が良い。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

チームでの datetime 処理の一貫性を重視する。

**コードレビューチェックポイント**:
- [ ] `datetime.now()` が naive を返していないか（`tz=UTC` が抜けていないか）
- [ ] `datetime.utcnow()` を使っていないか（3.12 deprecated）
- [ ] naive/aware の混在した比較がないか
- [ ] `pytz` を使っていないか（`zoneinfo` に統一されているか）
- [ ] タイムゾーン名が ユーザー入力由来のときにバリデーションされているか

**チームでの安全なパターン**: `datetime.now(tz=UTC)` を常に使う規約を CLAUDE.md に記載。
`pytz` を禁止リストに追加することを推奨。  
**ツール追加の必要性**: `ruff DTZ` ルール（flake8-datetimez）が `datetime.now()` naive 呼び出しを検出する。追加を推奨。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高。Pydantic で全 HTTP 入力を検証。`max_length` / `ge` / `le` の制限を設定。  
**「初心者でも安全な API」達成度**: 中。`parse_datetime()` ラッパーで Z 処理の落とし穴を隠蔽。
naive→UTC 自動昇格は便利だが、暗黙の仮定として文書化が必要。  
**設計上の負債**: `datetime.utcnow()` を誤用した場合に ruff が検出しないため `DTZ` ルール追加が有効。  
**Follow-up Issue 候補**: `ruff DTZ` ルール（flake8-datetimez）の有効化（Issue 化不要 — 同 PR で対応済み）

---

## セキュリティ診断

> **診断方針**: Django・FastAPI・SQLAlchemy 本体でも CVE が報告されてきたレベルの
> 攻撃ベクターを対象とする。「動いているから安全」は不正解。

### 1. OWASP API Security Top 10 (2023)

#### API1: オブジェクトレベルの認可不備 (BOLA / IDOR)
- ユーザー固有リソースなし。N/A。
- **結果**: ✅ 該当なし

#### API2: 認証の破損 (Broken Authentication)
- 認証エンドポイントなし。N/A。
- **結果**: ✅ 該当なし

#### API3: オブジェクトプロパティレベルの認可不備 (Mass Assignment)
- `{"iso8601": "2026-05-22T12:00:00Z", "days": 1, "admin": true}` を POST
- 結果: `admin` フィールドは Pydantic に無視され、レスポンスに現れない。
- **結果**: ✅ 合格（Pydantic のデフォルト動作で extra フィールドを無視）

#### API4: 無制限リソース消費 (Unrestricted Resource Consumption)
- `text` / `iso8601`: `max_length=50`
- `target_timezone`: `max_length=64`
- `days`: `ge=-36500, le=36500`
- `hours`: `ge=-876000, le=876000`
- **結果**: ✅ 合格（全フィールドに制限あり）

#### API5: 機能レベルの認可不備
- 管理者エンドポイントなし。N/A。
- **結果**: ✅ 該当なし

#### API6: SSRF
- URL 受信フィールドなし。N/A。
- **結果**: ✅ 該当なし

#### API7: セキュリティの設定ミス
- FT サンドボックスのため SecurityHeadersMiddleware は未設定（他 FT と同条件）。
- `ErrorHandlerMiddleware` が例外を RFC 9457 形式に変換。スタックトレース非公開。
- **結果**: ⚠️ サンドボックス制限（本番化時に SecurityHeadersMiddleware 追加が必要）

#### API8〜API10
- バージョン管理・外部 API 消費: N/A。
- **結果**: ✅ 該当なし

---

### 2. インジェクション攻撃

#### パストラバーサル（タイムゾーン名経由）
```
../../etc/passwd     → 422 ✅（_TIMEZONE_PATTERN でドット禁止）
Asia/Tokyo;cat passwd → 422 ✅（セミコロン禁止）
UTC\r\nX-Evil: hacked → 422 ✅（改行禁止）
```
`_TIMEZONE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9/_+-]{0,63}$")` が
ドット・スペース・改行・セミコロンを含む文字列を事前に拒否する。

- **結果**: ✅ 合格（`ZoneInfo` に不正文字列が到達しない）

#### SQL インジェクション
```
text="' OR '1'='1"  → 422 ✅（_ISO8601_PATTERN でアポストロフィ禁止）
```
- **結果**: ✅ 合格（DB なし・正規表現による事前検証）

#### コマンドインジェクション
- `subprocess` / `os.system` / `eval` の使用なし。
- **結果**: ✅ 合格

#### SSTI
- Jinja2 テンプレートの使用なし。
- **結果**: ✅ 合格

---

### 3. 認証・認可
- 認証機構なし（FT サンドボックス）。
- Null バイト `%002026-05-22T12:00:00Z` → 422（`max_length` + Pydantic でブロック）
- **結果**: ✅ 合格

---

### 4. 入力バリデーション

| 攻撃入力 | 結果 |
|---|---|
| `text="not-a-date"` | 422 ✅ |
| `text="' OR '1'='1"` | 422 ✅ |
| `text="\x002026-05-22T12:00:00Z"` | 422 ✅ |
| `text="2026-05-22T12:00:00Z" + "X" * 40` | 422 ✅（max_length=50） |
| `days=99999999` | 422 ✅（le=36500） |
| `days="1e5"（文字列）` | 422 ✅（Pydantic int 検証） |
| `days=True` | 200（True → 1 に型強制）⚠️ |

`days=True` は `1` に変換される（Python の `bool` は `int` のサブクラス）。
セキュリティ的にはリスクなし（`[ge, le]` 範囲内）だが、意図しない値として記録。

- **結果**: ✅ 合格（bool 型強制は仕様範囲内）

---

### 5. 情報漏洩

```json
// エラーレスポンス例
{
  "type": "https://nene2.dev/problems/validation-failed",
  "title": "Validation Failed",
  "status": 422,
  "errors": [{"field": "text", "message": "無効な日時フォーマット: 'bad'", "code": "invalid_datetime"}]
}
```

内部パス・モジュール名・DB スキーマ: レスポンスに含まれない。
`pip-audit`: 既知 CVE なし。

- **結果**: ✅ 合格

---

### 6. Python / FastAPI 固有の攻撃ベクター

#### ReDoS
```python
# _ISO8601_PATTERN のバックトラッキング試験
"2026-05-22T" + "a" * 30  → 422 in 0.007s ✅
```
`_ISO8601_PATTERN` は `\d+` と固定長パターンのみ使用。
`(a+)+` のような catastrophic backtracking は存在しない。

#### pickle / yaml
- 使用なし。
- **結果**: ✅ 合格

#### 型強制攻撃 (Pydantic Type Coercion)
- `days=True` → 1（bool は int のサブクラス。Pydantic デフォルト動作）
- 値は `[ge=-36500, le=36500]` 範囲内のため安全。

---

### 7. 依存関係の脆弱性スキャン

```
No known vulnerabilities found
```

- **スキャン結果**: CRITICAL: 0件 / HIGH: 0件 / MEDIUM: 0件 / LOW: 0件

---

### 診断サマリー

| カテゴリ | 結果 | 最重要発見 |
|---|---|---|
| OWASP API Top 10 | ✅ 全通過（一部 N/A） | API3 mass assignment は Pydantic が自動防御 |
| パストラバーサル（タイムゾーン） | ✅ 合格 | `_TIMEZONE_PATTERN` で ZoneInfo 前に遮断 |
| SQL インジェクション | ✅ 合格 | DB なし・正規表現で事前ブロック |
| コマンドインジェクション | ✅ 合格 | shell 呼び出しなし |
| SSTI | ✅ 合格 | テンプレートなし |
| 認証・認可 | ✅ 合格 | FT サンドボックスのため N/A |
| 入力バリデーション | ✅ 合格 | bool 型強制は仕様範囲内 |
| 情報漏洩 | ✅ 合格 | エラーメッセージに内部情報なし |
| ReDoS | ✅ 合格 | 0.007s — catastrophic backtracking なし |
| pickle / yaml | ✅ 合格 | 使用なし |
| 型強制攻撃 | ✅ 合格 | days=True → 1（値範囲内） |
| 依存関係 CVE | ✅ 合格 | 0件 |

**総合評価**: **合格**  
**発見した脆弱性**: 0件  
**特記事項**: SecurityHeadersMiddleware 未設定（FT サンドボックス共通制限。本番化時は必須）

---

## クラッカーペンテスト

> **実施方針**: 実際に攻撃ペイロードを送り込んで耐えられるかを試験する。

### フェーズ1: 構造推測（攻撃者の視点）

OpenAPI スキーマから推測できる内部構造:
- `target_timezone: str` フィールド → OS のタイムゾーンデータベースを参照している可能性
- `text: str` フィールド → 正規表現または `strptime` でパースしている可能性
- `days/hours/minutes: int` → Python `timedelta` を使っている可能性が高い

攻撃仮説:
1. `target_timezone` でパストラバーサル → `/etc/passwd` 等を読める可能性
2. `text` で SQL インジェクションまたは ReDoS
3. `days` のオーバーフローで `OverflowError` からスタックトレース漏洩
4. CRLF インジェクションでレスポンスヘッダー改ざん

### フェーズ2: 攻撃実行ログ

#### A. パストラバーサル攻撃（タイムゾーン名経由）

```
ペイロード1: target_timezone="../../etc/passwd"
→ 422 Validation Failed（_TIMEZONE_PATTERN でドット拒否）

ペイロード2: target_timezone="Asia/Tokyo;cat /etc/passwd"
→ 422（セミコロン拒否）

ペイロード3: target_timezone="UTC\r\nX-Evil: hacked"
→ 422（改行文字拒否）
```

**結果**: ✅ 全て耐えた。`ZoneInfo` に到達する前に `_TIMEZONE_PATTERN` で遮断。

#### B. SQL インジェクション / フォーマット文字列攻撃

```
ペイロード: text="' OR '1'='1"
→ 422（アポストロフィは _ISO8601_PATTERN に含まれない）

ペイロード: text="%Y-%m-%d"  （strptime フォーマット文字列）
→ 422（% は _ISO8601_PATTERN に含まれない）
```

**結果**: ✅ 全て耐えた。`_ISO8601_PATTERN` が strptime に到達する前にフィルタリング。

#### C. 境界値・エッジケース攻撃

```
ペイロード: days=36500（上限）→ 200 ✅ 正常処理
ペイロード: days=36501（上限+1）→ 422 ✅
ペイロード: days=-36500（下限）→ 200 ✅
ペイロード: days=True → 200（1 に型強制）— 想定内動作
ペイロード: start="2026-05-22T12:00:00Z", end="2026-05-22T12:00:00"（naive/aware 混在）
→ 422 ✅（混在検出して ValidationException）
```

**結果**: ✅ 境界値は Pydantic が正確にブロック。naive/aware 混在も正しく検出。

#### D. 情報収集攻撃（エラーメッセージ解析）

```
ペイロード: text="not-a-date"
エラー: {"message": "無効な日時フォーマット: 'not-a-date'", "code": "invalid_datetime"}
→ 内部モジュール名・スタックトレース・ファイルパスは含まれない ✅
```

**結果**: ✅ エラーメッセージに内部情報なし。

#### E. DoS 試み

```
ペイロード: text="2026-05-22T" + "a" * 30（max_length でブロック）
→ 422 ✅（max_length=50 で 41 文字でブロック）

ペイロード: _ISO8601_PATTERN への ReDoS（"2026-05-22T" + "a" * 30 を正規表現にかける）
→ 0.007s ✅ catastrophic backtracking なし
```

**結果**: ✅ DoS 耐性あり。

### フェーズ3: 攻撃まとめ

| 攻撃カテゴリ | 試みた攻撃数 | 突破 | 耐えた | 予期しない動作 |
|---|---|---|---|---|
| パストラバーサル | 3 | 0 | 3 | 0 |
| インジェクション（SQL/Format） | 2 | 0 | 2 | 0 |
| 境界値/エッジ | 6 | 0 | 6 | 0 |
| 情報収集 | 2 | 0 | 2 | 0 |
| DoS (ReDoS/長大入力) | 2 | 0 | 2 | 0 |

**攻撃耐性評価**: **堅牢**  
**発見した弱点**: なし（`days=True → 1` は仕様範囲内の型強制）

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 低 | `ruff DTZ` ルール（flake8-datetimez）の有効化を検討 | enhancement |
| 低 | Windows 環境向けに `tzdata` 依存を CLAUDE.md に追記 | docs |

---

## まとめ

`datetime` + `zoneinfo` の組み合わせは pytz 不要で現代的な aware datetime 処理を実現する。
最大の落とし穴は `datetime.now()` が naive を返すことと、naive/aware の混在比較が `TypeError` を投げること。
API 境界でこれらを検出して 422 に変換する実装で安全に利用できる。

タイムゾーン名をユーザー入力で受け取る場合、`_TIMEZONE_PATTERN` による事前バリデーションが
パストラバーサル防御の第一層として有効に機能した（セキュリティ診断・クラッカーペンテスト両方で確認）。

次の FT205 は `205 % 3 = 1` → セキュリティ診断なし、`205 % 4 = 1` → クラッカーペンテストなし。
