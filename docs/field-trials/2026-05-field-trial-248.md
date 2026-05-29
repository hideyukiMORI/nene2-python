# FT248: string.Formatter — format string 攻撃の防御

**日付**: 2026-05-29
**テーマ**: Python `string.Formatter` の format string 攻撃と hardened Formatter の実装と検証
**セキュリティ診断**: なし（248 % 3 = 2）
**クラッカーペンテスト**: 🔍 あり（248 % 4 = 0）

---

## 概要

`str.format` / `string.Formatter` に**ユーザー制御のフォーマット文字列**を渡すと、`{0.__class__.__init__.__globals__}` で**オブジェクト内部・グローバル名前空間に到達**でき、設定値や秘密鍵の漏洩・RCE の足がかりになる（既知の format string 攻撃）。FT236（`string.Template` は式評価しないため安全）と対をなし、本 FT では `Formatter` をサブクラス化して**属性/添字/位置参照を禁止し幅パディング DoS を制限**する hardened 実装を、ペンテストで検証した。

| 危険 | 安全（本 FT） |
|---|---|
| `"{0.__class__...}".format(obj)` | `_SafeFormatter`（識別子フィールドのみ） |
| `"{:>1000000000}"`（幅爆弾） | 幅・精度の上限チェック |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft248-string-formatter/`

| 要素 | 概要 |
|---|---|
| `_SafeFormatter.get_field` | `field_name.isidentifier()` のみ許可（`.`/`[]`/位置を拒否） |
| `_SafeFormatter.format_field` | format_spec 内の数値（幅・精度）が 1000 超なら拒否 |
| `render_template()` | 名前付き値のみで安全にレンダリング |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/format/render` | hardened Formatter でレンダリング |

---

## 摩擦点

### F-1: `get_field` をオーバーライドし属性/添字/位置参照を禁止

**観察**: `Formatter.get_field("0.__class__", ...)` は `args[0].__class__` を返す。`{name.__class__.__init__.__globals__}` でモジュールのグローバル（DB 接続文字列・秘密鍵など）に到達できる。デフォルトの `str.format` はこれを許す。

**対処**: `get_field` を override し `field_name.isidentifier()`（`.`/`[`/数字を含まない単純名）でない場合は `ValueError`。名前付きフィールドのみ kwargs から解決。ペンテストで attr/globals/mro/index/位置/auto-number がすべて 422。

### F-2: `format_field` で幅・精度パディング爆弾を制限

**観察**: `"{:>999999999}".format("x")` は約 10 億文字の文字列を生成し**メモリ枯渇 DoS**。テンプレート自体は短いので長さ制限では防げない。

**対処**: `format_field` を override し format_spec 内の数値（幅・精度）が `MAX_FIELD_WIDTH=1000` を超えたら拒否。幅 1e9 を **4ms** で 422（生成前に遮断）。

### F-3: `string.Template`（FT236）との使い分け

**観察**: 単純な `$name` 置換でよいなら `string.Template`（式評価せず最も安全）。書式指定（桁揃え・ゼロ埋め）が必要なら Formatter だが、**ユーザーがフォーマット文字列を制御する場合は hardened 必須**。

**対処**: 用途で選択。フォーマット文字列が開発者管理なら通常の `str.format` でよいが、ユーザー由来なら `_SafeFormatter` を通す。

---

## クラッカーペンテスト

### フェーズ1: 構造推測

`/format/render` から format ベースのテンプレートエンジンと推測。`{x.__class__...}` の属性到達・幅爆弾を狙う。

### フェーズ2: 攻撃実行ログ

| カテゴリ | ペイロード | 結果 |
|---|---|---|
| 属性到達 | `{name.__class__}` | **422** |
| globals 到達 | `{name.__class__.__init__.__globals__}` | **422** |
| mro | `{name.__class__.__mro__}` | **422** |
| 添字 | `{name[0]}` | **422** |
| 位置参照 | `{0}` | **422** |
| auto-number | `{}` | **422** |
| 幅爆弾 | `{n:>999999999}` | **422 / 4ms**（生成前に遮断） |
| 精度爆弾 | `{n:.9999999}` | **422** |
| 正常: 名前付き | `Hi {name} ({age})` | 200 |
| 正常: spec | `{n:>5}\|{m:04d}` | 200（`    x\|0003`） |
| 正常: 変換 | `{n!r}` | 200 |
| 未定義 | `{missing}` | **422** |
| 不正構文 | `{unclosed` | **422** |

### フェーズ3: まとめ

| 攻撃カテゴリ | 試行 | 突破 | 耐えた |
|---|---|---|---|
| 属性/添字/位置到達 | 6 | 0 | 6 |
| 幅・精度 DoS | 2 | 0 | 2 |
| 不正入力 | 2 | 0 | 2 |

**攻撃耐性評価**: 堅牢
**発見した弱点**: なし。`get_field` の識別子制限で内部到達を全遮断、`format_field` の幅制限でパディング爆弾を遮断。正常な書式指定は維持。

---

## テスト結果

```
8 passed in 0.30s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`{name}` で埋め込むのは身近。`.format` がオブジェクト内部に到達できる危険は知らないことが多い。

**ドキュメント理解**: 攻撃例をコメントで明示。
**事故リスク（高）**: ユーザー入力を `.format` のテンプレートに使う。
**規約の使いやすさ**: template + values が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

通知文面テンプレートで `user_template.format(**data)` をやりがち。hardened Formatter が代替。

**コピペ可能性**: `_SafeFormatter` は流用可。
**拡張時の罠**: 生 `.format` への回帰・幅爆弾。
**事故リスク（高）**: format string 攻撃。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

テンプレートリテラルと違い Python の `.format` は属性アクセスできてしまう点が驚き。

**エラーレスポンスの質**: 攻撃・不正は 422。
**Python 固有概念**: format mini-language・get_field。
**事故リスク（低）**: hardened で防御。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

format string 攻撃は有名（settings.SECRET_KEY 漏洩等）。ユーザーテンプレートは Template か hardened Formatter、という判断は妥当。

**他フレームワークとの差異**: ログフォーマットや i18n でも同種の注意。
**nene2 の薄さへの評価**: get_field/format_field の override で攻撃面を原理的に絞る設計が良い。
**事故リスク（低）**: ペンテストで全遮断。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- ユーザー入力を `.format`/f-string のテンプレートに使っていないか（format string 攻撃）。
- 使うなら `get_field` で属性/添字/位置を禁止しているか。
- 幅・精度の上限（パディング爆弾）。
- 単純置換なら `string.Template`（FT236）を優先。

**チームでの安全なパターン**: ユーザーテンプレート=Template、書式必要時=hardened Formatter、開発者管理=通常 format。
**事故リスク（低）**: 全攻撃を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `eval`/`exec` 不使用・Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。format string 攻撃の遮断は「Security first」。
**初心者でも安全な API 達成度**: get_field/format_field の制限を関数内に隠蔽し、内部到達・DoS の余地を排除。
**改善提案**: 「ユーザーテンプレートの安全な扱い」how-to に Template / hardened Formatter / 通常 format の選択フローを記載し、FT236 と相互リンクする。
