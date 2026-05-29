# FT246: unicodedata — NFKC 正規化 / homoglyph / 制御文字検出

**日付**: 2026-05-29
**テーマ**: Python `unicodedata` の正規化・カテゴリ判定とスプーフィング対策の実装と検証
**セキュリティ診断**: 🔒 あり（246 % 3 = 0）
**クラッカーペンテスト**: なし（246 % 4 = 2）

---

## 概要

`unicodedata` は Unicode 文字の正規化（NFKC 等）・カテゴリ判定を提供する。HTTP API でラップし、入力文字列の Unicode 検査と「安全な識別子」検証を行った。診断回（246 % 3 = 0）として **ゼロ幅・双方向制御（RTL override）・制御文字・homoglyph（混在スクリプト）** によるスプーフィングを検証した。

| API | ユースケース |
|---|---|
| `unicodedata.normalize("NFKC", s)` | 互換正規化（全角→半角・合字分解） |
| `unicodedata.category(c)` | 文字カテゴリ（Cc 制御 / Cf 書式 / Lu,Ll 文字 / Nd 数字 等） |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft246-unicodedata/`

| 関数 | 概要 |
|---|---|
| `inspect_text()` | NFKC 差・ASCII 判定・制御/書式文字・カテゴリ集合 |
| `safe_identifier()` | NFKC 正規化 + 許可カテゴリ（L*/Nd）のみ、制御/書式文字を拒否 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/unicode/inspect` | Unicode 検査 |
| POST | `/unicode/safe-identifier` | 安全な識別子検証 |

---

## 摩擦点

### F-1: ゼロ幅・双方向制御・制御文字を category（Cf/Cc）で検出・拒否

**観察**: ゼロ幅スペース（U+200B, Cf）・ゼロ幅接合子（U+200D）・RTL override（U+202E, Cf）・制御文字（Cc）は、見た目に現れず**ユーザー名スプーフィング・ファイル名偽装・ログ偽装**に悪用される。素の文字列比較では検出できない。

**対処**: `unicodedata.category(char)` で `Cf`（書式）/`Cc`（制御）を検出。識別子では許可カテゴリ（`Lu,Ll,Lt,Lm,Lo,Nd`）以外を 422。診断でゼロ幅・RTL・制御・記号がすべて拒否されることを確認。

### F-2: NFKC で「別名に化ける」— 正規化は比較前に一度だけ一貫適用

**観察**: NFKC は全角 `ＡＤＭＩＮ`→`ADMIN`、合字 `ﬁle`→`file`、上付き `x²`→`x2` のように**見た目の異なる入力を同一化**する。正規化を比較の片側だけに適用したり、保存と検証で適用タイミングがずれると、検証回避（`ＡＤＭＩＮ` で admin になりすます）が起きる。

**対処**: 識別子は**保存・比較前に必ず NFKC 正規化**してから検証。`changed_by_nfkc` で正規化差を可視化。全角・合字が正規化されることを確認。

### F-3【重要・限界】NFKC + カテゴリ検査は homoglyph（混在スクリプト）を防げない

**観察**: キリル文字 `а`(U+0430) + `dmin` = `аdmin` は ASCII `admin` と**見た目が同一**だが別文字列。category は両方 `Ll`（小文字）なので `safe_identifier` を **通過してしまう**（診断で 200・正規化後も Cyrillic のまま）。NFKC でも別スクリプトの混在は同一化されない。さらに **`unicodedata` には「スクリプト判定 API がない」**ため、純標準ライブラリだけでは混在スクリプト検出が困難。

**対処（限界の明示）**: 本 FT の `safe_identifier` は制御/書式/記号は防ぐが **homoglyph は防げない**（条件付き合格）。confusable 対策が必要な文脈では:
1. 高セキュリティ用途では**識別子を ASCII に限定**（`value.isascii()`）する、
2. または Unicode TR39（confusable skeleton）・`idna`・`confusable-homoglyphs` 等の専用ライブラリを併用する、
3. 少なくとも非 ASCII 識別子は**レビュー・単一スクリプト強制**の対象にする。
この限界を how-to に明記する。

---

## セキュリティ診断結果

| カテゴリ | 例 | 結果 |
|---|---|---|
| ゼロ幅スペース（Cf） | `ad‹U+200B›min` | inspect: has_format / identifier: **422** |
| RTL override（Cf） | `a‹U+202E›b` | has_format / **422** |
| ゼロ幅接合子（Cf） | `a‹U+200D›b` | has_format=True |
| 制御文字（Cc） | `a\x00\tb` | has_control / identifier: **422** |
| 記号・句読点 | `a;b` | identifier: **422** |
| 空（正規化後） | `‹U+200B›` のみ | **422** |
| 長さ超過 | 1,001 文字 | **422** |
| NFKC 正規化 | 全角 `ＡＤＭＩＮ`→`ADMIN` / `ﬁle`→`file` / `x²`→`x2` | 正規化される |
| **homoglyph（F-3）** | キリル `аdmin` | **200（通過）= 限界** |
| セキュリティヘッダー | — | 付与あり |

**総合評価: 条件付き合格**

制御・書式・記号・正規化回避は遮断。ただし **homoglyph（混在スクリプト）は NFKC + category だけでは防げない**（F-3、stdlib の限界）。confusable 対策は ASCII 限定または TR39/専用ライブラリで補う旨を明記。

---

## テスト結果

```
9 passed in 0.30s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

> 余談: テスト内にゼロ幅・RTL override をリテラルで埋めると ruff の `PLE2515`/`PLE2502`（不可視・制御文字の混入）に弾かれた。`"​"` 等のエスケープに修正。lint も Unicode スプーフィングを検出してくれる好例。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

「見えない文字」が攻撃に使われると知るのは衝撃。ゼロ幅・RTL の存在を学べる。

**ドキュメント理解**: category コード（Cc/Cf）は表で補足。
**事故リスク（高）**: ゼロ幅・homoglyph を素通りさせる。
**規約の使いやすさ**: text → 検査結果が明快。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

ユーザー名・ファイル名検証で使う。homoglyph の限界を知らないと「正規化したから安全」と誤認。

**コピペ可能性**: `safe_identifier` は流用可（ただし homoglyph 限界を理解して）。
**拡張時の罠**: NFKC を片側だけ適用・homoglyph 未対応。
**事故リスク（中〜高）**: 混在スクリプトのなりすまし。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`String.prototype.normalize('NFKC')` に対応。表示名の偽装（RTL）は UI でも問題。

**エラーレスポンスの質**: 不正文字種は 422。
**Python 固有概念**: category・NFKC。
**事故リスク（中）**: homoglyph。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

アカウント乗っ取り（homoglyph ドメイン・ユーザー名）対策で TR39 skeleton や単一スクリプト強制が必要なことを把握。stdlib にスクリプト API がない限界は妥当な指摘。

**他フレームワークとの差異**: confusable 対策は専用ライブラリ依存。
**nene2 の薄さへの評価**: 制御/書式の遮断は良い。homoglyph 限界を明示する姿勢が誠実。
**事故リスク（中）**: 高セキュリティ用途は ASCII 限定推奨。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- 識別子を保存・比較前に NFKC 正規化し、一貫して適用しているか。
- ゼロ幅・双方向制御・制御文字（Cf/Cc）を拒否しているか。
- homoglyph（混在スクリプト）対策の要否を判断しているか（ASCII 限定 or TR39）。
- ログ・表示で RTL override による偽装が起きないか。

**チームでの安全なパターン**: 識別子は「NFKC + カテゴリ検査 + （高セキュリティでは）ASCII 限定」。confusable は専用ライブラリ。
**事故リスク（中）**: homoglyph を CLAUDE.md/how-to で注意喚起。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: 入力検証・`ValidationException` 変換・`logging` 使用は準拠。Unicode スプーフィングは「入力バリデーション」診断カテゴリ（Unicode RTL）に該当。
**初心者でも安全な API 達成度**: 制御/書式/記号は関数内で遮断。homoglyph は stdlib の限界として明示し誤った安心を与えない。
**改善提案**: how-to「識別子の安全な検証」に NFKC・カテゴリ検査・ASCII 限定・TR39 の段階的対策を記載し、本 FT の F-3 限界を共有する。
