# FT244: html.parser — HTMLParser で信頼できない HTML を解析

**日付**: 2026-05-29
**テーマ**: Python `html.parser` の HTML 解析・テキスト抽出の実装と検証
**セキュリティ診断**: なし（244 % 3 = 1）
**クラッカーペンテスト**: 🔍 あり（244 % 4 = 0）

---

## 概要

`html.parser.HTMLParser` は HTML を**トークン化**するイベント駆動パーサ。HTML からプレーンテキストを安全に抽出する用途を検証した。重要な前提: **html.parser はトークナイザでありサニタイザではない** — 安全な HTML を出力したいなら専用ライブラリ（`nh3`/`bleach`）を使う。本 FT はテキスト抽出（`<script>`/`<style>` の内容を除外）に限定し、コードは一切実行しない。ペンテスト回（244 % 4 = 0）として script 漏洩・DoS・不正 HTML を攻撃した。

| API | ユースケース |
|---|---|
| `HTMLParser.feed()` | HTML を逐次解析 |
| `handle_starttag/endtag/data` | タグ・テキストのコールバック |
| `convert_charrefs=True` | 文字参照（`&amp;`）を自動デコード |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft244-html-parser/`

| 要素 | 概要 |
|---|---|
| `_TextExtractor` | テキスト抽出、`script`/`style` 内容を `_skip_depth` で除外 |
| `extract_text()` | プレーンテキスト・タグ数・ユニークタグを返す |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/html/extract-text` | HTML からテキスト抽出 |

---

## 摩擦点

### F-1: `handle_data` は `<script>`/`<style>` の内容も拾う — 明示除外が必要

**観察**: 素朴に `handle_data` を集めると `<script>alert(1)</script>` の `alert(1)` も「テキスト」として混入する。これを抽出結果として表示・再利用すると JS コードが漏れる。

**対処**: `script`/`style` タグの開閉を `_skip_depth` で追跡し、その内側の `handle_data` を捨てる。ペンテストで basic/大文字 SCRIPT/ネスト/style いずれも内容が除外されることを確認。

### F-2: html.parser はサニタイザではない — 出力用途は専用ライブラリ

**観察**: html.parser は解析するだけで、危険な属性（`onerror=`）やタグを除去した**安全な HTML を生成**する機能はない。テキスト抽出は安全だが、「HTML を受け取り安全な HTML を返す」サニタイズには不十分。

**対処**: 本 FT はテキスト抽出に限定。安全な HTML 出力が要る場合は `nh3`（Rust 製・推奨）や `bleach` を使う旨をドキュメント化。属性ベース XSS（`onerror`）はテキスト抽出では出力に現れないが、サニタイズ用途では別途対処が必要。

### F-3: 不正・壊れた HTML でも例外を出さない（寛容）

**観察**: `<div><p>broken`（未閉じ）や `a < b > c`（裸の不等号）でも `HTMLParser` は例外を出さず寛容に処理する。エラーで気付けないが、テキスト抽出用途では利点。

**対処**: 寛容性を許容しつつ入力長を制限。`convert_charrefs=True` で `&amp;`→`&` 等を正しくデコード。

---

## クラッカーペンテスト

### フェーズ1: 構造推測

`/html/extract-text` から HTML パーサと推測。script 内容の漏洩・タグ数 DoS・不正 HTML での例外を狙う。

### フェーズ2: 攻撃実行ログ

| カテゴリ | ペイロード | 結果 |
|---|---|---|
| script 漏洩 | `<script>alert(1)</script>hi` | `'hi'`（script 除外） |
| 大文字 SCRIPT | `<SCRIPT>steal()</SCRIPT>ok` | `'ok'`（除外） |
| ネスト script | `<script><script>x</script></script>visible` | `'visible'`（除外） |
| style 漏洩 | `<style>...</style>txt` | `'txt'`（除外） |
| 属性 XSS | `<img src=x onerror=alert(1)>caption` | `'caption'`（属性は data に出ない） |
| 未閉じ | `<div><p>broken` | `'broken'`（例外なし） |
| 裸の不等号 | `a < b > c` | `'a < b > c'`（寛容） |
| エンティティ | `AT&T &copy; 2026` | `'AT&T © 2026'`（デコード） |
| コメント | `<!-- secret -->shown` | `'shown'`（コメント除外） |
| DoS 3万タグ | `<b>`×30,000 | **200 / 55ms**（長さ上限内） |
| DoS 2万ネスト | `<div>`×20,000... | **422**（長さ上限超過） |
| 長さ超過 | 100,001 文字 | **422** |

### フェーズ3: まとめ

| 攻撃カテゴリ | 試行 | 突破 | 耐えた |
|---|---|---|---|
| script/style 漏洩 | 5 | 0 | 5 |
| 不正 HTML | 4 | 0 | 4 |
| DoS | 3 | 0 | 3 |

**攻撃耐性評価**: 堅牢
**発見した弱点**: なし。script/style 内容の除外・入力長制限が機能。html.parser は解析専用であり、HTML サニタイズには `nh3`/`bleach` を使う旨を明記。

---

## テスト結果

```
7 passed in 0.86s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

HTML からテキストを取り出すのは分かりやすい。script の中身が混ざる罠は気付きにくい。

**ドキュメント理解**: 「パーサ ≠ サニタイザ」をコメントで明示。
**事故リスク（中）**: script 内容を抽出に含める／html.parser でサニタイズしたつもりになる。
**規約の使いやすさ**: html → text が直感的。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

スクレイピングや本文抽出で使う。script 除外を忘れて JS をテキスト扱いしがち。

**コピペ可能性**: `_TextExtractor` は流用可。
**拡張時の罠**: script/style 除外漏れ・サニタイズ誤用。
**事故リスク（中）**: サニタイザと誤認。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

DOMParser に対応。`textContent` 相当を得る感覚。XSS サニタイズは DOMPurify（≒nh3）が要る。

**エラーレスポンスの質**: 長さ超過は 422。
**Python 固有概念**: イベント駆動パーサ・convert_charrefs。
**事故リスク（低）**: 抽出は安全。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

本文抽出は html.parser/lxml、サニタイズは nh3/bleach、と用途を分ける。XXE は HTML には無いが XML は別（defusedxml, FT180）。

**他フレームワークとの差異**: lxml は高速だが C 依存。標準 html.parser は軽量。
**nene2 の薄さへの評価**: 抽出に限定し script 除外を組み込んだ設計が妥当。
**事故リスク（低）**: ペンテスト堅牢。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `script`/`style` の内容を抽出に含めていないか。
- html.parser を「サニタイザ」として使っていないか（出力は nh3/bleach）。
- 入力長・タグ数の上限（DoS）。
- 抽出テキストを再表示する際の HTML エスケープ（FT229）。

**チームでの安全なパターン**: 抽出=html.parser、サニタイズ=nh3、表示=html.escape の三段を明文化。
**事故リスク（低）**: script 除外・上限を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 長さ制限・`ValidationException` 変換・`logging` 使用は準拠。コードを実行しない解析専用設計は安全。
**初心者でも安全な API 達成度**: script/style 除外を組み込み、抽出用途での JS 漏洩を防止。
**改善提案**: 「HTML の扱い early 表」（抽出=html.parser / サニタイズ=nh3 / エスケープ=html.escape / XML=defusedxml）を how-to にまとめ、FT229・FT180 と相互リンクする。
