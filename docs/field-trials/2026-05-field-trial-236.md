# FT236: string.Template — substitute / safe_substitute（SSTI 安全）

**日付**: 2026-05-29
**テーマ**: Python `string.Template` のテンプレート置換と SSTI 安全性の実装と検証
**セキュリティ診断**: なし（236 % 3 = 2）
**クラッカーペンテスト**: 🔍 あり（236 % 4 = 0）

---

## 概要

`string.Template` は `$name` / `${name}` 形式の**純粋な名前置換**を行う。`str.format`（`{0.__class__}` で属性到達可能）や eval ベースのテンプレートと異なり、**式評価・属性アクセスを一切行わない**ため SSTI（Server-Side Template Injection）に対して構造的に安全。ペンテスト回（236 % 4 = 0）として、ユーザー提供テンプレートに各種 SSTI ペイロードを投入し評価されないことを確認した。

| API | ユースケース |
|---|---|
| `Template(s).substitute(map)` | 厳格置換（未定義変数は `KeyError`） |
| `Template(s).safe_substitute(map)` | 安全置換（未定義変数は `$name` のまま残す） |
| `$$` | リテラル `$` のエスケープ |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft236-string-template/`

| 関数 | 概要 |
|---|---|
| `render_strict()` | `substitute`、未定義/不正記法は `ValueError` → 422 |
| `render_safe()` | `safe_substitute`、未定義は `$name` のまま |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/template/render` | 厳格レンダリング |
| POST | `/template/render-safe` | 安全レンダリング |

---

## 摩擦点

### F-1: `string.Template` は SSTI 安全 — だが `str.format` / Jinja は危険

**観察**: ユーザー提供テンプレートのレンダリングで `str.format` を使うと `"{0.__class__.__init__.__globals__}".format(obj)` で**オブジェクト内部・グローバルに到達**でき RCE につながる（既知の format string 攻撃）。Jinja2 も `{{7*7}}` を評価する。`string.Template` は `$name` を値に置換するだけで**式評価も属性アクセスもしない**。

**対処**: ユーザーがテンプレート文字列を制御する場面では `string.Template` を使う。本 FT のペンテストで `${x.__class__}`・`{0.__class__}`・`${7*7}`・`{{7*7}}` がすべて**リテラルのまま**残る（評価されない）ことを確認。

### F-2: 単一パス置換 — 値に `$` を含めても再帰展開されない

**観察**: `$v`（mapping `{"v": "${other}"}`）をレンダリングすると結果は `${other}` で、**`other` は再置換されない**。`string.Template` は 1 回だけ置換するため、値経由のネストしたテンプレートインジェクションが成立しない。

**対処**: 単一パス挙動を信頼。再帰展開する独自エンジンを作らない限り安全。

### F-3: `substitute` の未定義変数は `KeyError`、不正記法は `ValueError`

**観察**: `substitute` は未定義変数で `KeyError`、`$ ` や `$123` のような不正な placeholder で `ValueError`。`safe_substitute` は未定義を残すが不正記法は同様に扱う。

**対処**: 両例外を捕捉して 422。`safe_substitute` は表示崩れの許容できる用途、`substitute` は全変数必須の用途で使い分け。

---

## クラッカーペンテスト

### フェーズ1: 構造推測

`/template/render` `/render-safe` からテンプレートエンジンと推測。SSTI（式評価・属性到達）・ネストインジェクション・DoS を狙う。

### フェーズ2: 攻撃実行ログ

| カテゴリ | ペイロード | 結果 |
|---|---|---|
| 属性到達 | `${x.__class__.__mro__}` | **リテラル**（`x` 置換のみ、`.→...` は文字列） |
| globals 到達 | `${x.__init__.__globals__}` | **リテラル** |
| format-style | `{x.__class__}` / `{0.__class__.__bases__}` | **完全リテラル**（`{}` は無意味） |
| 算術評価 | `${7*7}` | **リテラル**（`49` にならない） |
| Jinja 風 | `{{7*7}}` | **リテラル** |
| f-string 風 | `f'{7*7}'` | **リテラル** |
| import | `$__import__` | safe で残る / strict で 422 |
| ネスト注入 | `$v`={"v":"${other}"} | **`${other}`**（再展開なし・F-2） |
| 未定義（strict） | `$secret` | **422** |
| 不正記法（strict） | `$ $123 $` | **422** |
| DoS | template 10,001 / vars 101 | **422** |

### フェーズ3: まとめ

| 攻撃カテゴリ | 試行 | 突破 | 耐えた |
|---|---|---|---|
| SSTI（式評価・属性到達） | 7 | 0 | 7 |
| ネスト/値経由注入 | 1 | 0 | 1 |
| 不正入力（strict） | 2 | 0 | 2 |
| DoS | 2 | 0 | 2 |

**攻撃耐性評価**: 堅牢
**発見した弱点**: なし。`string.Template` は式評価を行わず単一パス置換のため SSTI に構造的に安全。

---

## テスト結果

```
6 passed in 0.87s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`$name` 置換は分かりやすい。`safe_substitute` と `substitute` の違い（未定義の扱い）が学びやすい。

**ドキュメント理解**: SSTI の概念は高度だがコメントで「式評価しない」と明示。
**事故リスク（低）**: Template 自体は安全。むしろ `str.format`/f-string をユーザー入力に使う方が危険。
**規約の使いやすさ**: template + mapping が直感的。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

メールテンプレートや通知文面で使う。`f"{user_template}"` や `.format(**data)` をユーザー入力でやると事故る。Template が安全な代替。

**コピペ可能性**: render_strict/safe は流用可。
**拡張時の罠**: 「便利だから」と Jinja や format に乗り換えると SSTI を持ち込む。
**事故リスク（低）**: Template 使用なら安全。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

テンプレートリテラルに似るが、サーバー側でユーザーテンプレートを評価する危険性を理解する契機。

**エラーレスポンスの質**: 未定義/不正は 422。
**Python 固有概念**: `$name` 記法・単一パス置換。
**事故リスク（低）**: 評価されない。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

SSTI は Jinja2 の `{{}}` で多発する重大脆弱性。ユーザーがテンプレートを制御するなら `string.Template` 一択、という判断は正しい。

**他フレームワークとの差異**: Jinja2 は SandboxedEnvironment でも回避例あり。Template は式を持たないため攻撃面が原理的にない。
**nene2 の薄さへの評価**: 安全なプリミティブを薄くラップする良い例。
**事故リスク（低）**: ペンテストで全 SSTI 無効化を確認。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- ユーザー制御テンプレートに `str.format`/`%`/f-string/Jinja を使っていないか — SSTI。`string.Template` を使う。
- 値経由のネスト展開を独自実装していないか（再帰展開は危険）。
- `substitute`/`safe_substitute` の使い分け（未定義の扱い）。
- テンプレート長・変数数の上限。

**チームでの安全なパターン**: 「ユーザーテンプレート = string.Template」をルール化し、format/Jinja の動的テンプレートを lint で警告。
**事故リスク（低）**: 全 SSTI をペンテスト回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `eval`/`exec` 不使用・Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。式評価しない Template は「セキュリティは設計の出発点」を体現。
**初心者でも安全な API 達成度**: 評価機構を持たない Template を採用し、SSTI の余地を原理的に排除。
**改善提案**: how-to に「ユーザー提供テンプレートは `string.Template`、`str.format`/Jinja の動的テンプレートは禁止」を明記し、FT231（shlex）と並ぶ「危険プリミティブ回避」シリーズに加える。
