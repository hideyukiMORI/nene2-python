# FT230: difflib — unified_diff / SequenceMatcher / get_close_matches

**日付**: 2026-05-29
**テーマ**: Python `difflib` モジュールの差分・類似度・あいまい検索の実装と検証
**セキュリティ診断**: なし（230 % 3 = 2）
**クラッカーペンテスト**: なし（230 % 4 = 2）

---

## 概要

`difflib` はテキスト差分・類似度計算・あいまい一致を提供する。HTTP API でラップし unified diff・類似度・近似候補検索を検証した。注意点は `SequenceMatcher.ratio()` が **O(n²)** であり、長大入力で CPU を消費する点（入力長制限が必要）。

| API | ユースケース |
|---|---|
| `difflib.unified_diff(a_lines, b_lines)` | unified 形式のテキスト差分 |
| `difflib.SequenceMatcher(None, a, b).ratio()` | 類似度（0.0〜1.0） |
| `difflib.get_close_matches(word, candidates)` | あいまい一致候補 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft230-difflib/`

| 関数 | 概要 |
|---|---|
| `make_unified_diff()` | `splitlines(keepends=True)` で行リスト化し unified diff を生成 |
| `similarity_ratio()` | `SequenceMatcher.ratio()` を 4 桁丸めで返す |
| `find_close_matches()` | `get_close_matches(n=3, cutoff=0.6)` |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/diff/unified` | unified diff |
| POST | `/diff/ratio` | 類似度 |
| POST | `/diff/close-matches` | あいまい候補検索 |

---

## 摩擦点

### F-1: `unified_diff` は「文字列」ではなく「行のリスト」を取る

**観察**: `unified_diff(a, b)` に文字列をそのまま渡すと、文字単位で diff されてしまう（文字列はイテレートすると 1 文字ずつ）。意図した行単位 diff にならない。

**対処**: `text.splitlines(keepends=True)` で行リストに変換してから渡す。`keepends=True` で改行を保持しないと "No newline at end of file" 的なズレが出る。出力は `rstrip("\n")` で整形して JSON 配列で返す。

### F-2: `SequenceMatcher.ratio()` は O(n²) — 入力長制限が必須

**観察**: `ratio()` の計算量は最悪 O(n²)。数 MB のテキスト 2 つを渡すと CPU を専有し DoS になり得る。`difflib` 自体に上限はない。

**対処**: 入力長を `MAX_TEXT_LENGTH = 20_000`（diff/ratio 共通）と控えめに制限。Pydantic と関数内で二重検証。`quick_ratio()`/`real_quick_ratio()` で上限を先に見積もる手もある。

### F-3: `get_close_matches` の `cutoff`/`n` と候補数

**観察**: `get_close_matches(word, possibilities, n=3, cutoff=0.6)` の `cutoff` を下げすぎると無関係な候補が混じり、候補リストが巨大だと O(候補数 × n²) になる。

**対処**: 候補数上限（100）・各候補長上限・`cutoff=0.6` の既定で精度と性能を確保。

---

## テスト結果

```
7 passed in 0.82s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

diff の `+`/`-` 行は git の差分でお馴染みなので理解しやすい。類似度 0.0〜1.0 も直感的。

**ドキュメント理解**: 「文字列ではなく行リストを渡す」点は最初つまずく。コメントで明示。
**事故リスク（低）**: 破壊的操作はない。長大入力の CPU 消費に注意。
**規約の使いやすさ**: before/after を送ると diff 行が返る形は分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

設定ファイルの差分表示やタイプミス補正（コマンド候補）で使う。`get_close_matches` は CLI のサジェストに便利。

**コピペ可能性**: 3 関数とも流用しやすい。
**拡張時の罠**: `unified_diff` に文字列直渡し。`ratio` の O(n²)。
**事故リスク（低）**: 入力長制限を外すと CPU DoS。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`diff` ライブラリ（jsdiff）に対応。unified 形式はそのまま差分ビューアに流せる。

**エラーレスポンスの質**: 長さ/候補数超過は 422 で明確。
**Python 固有概念**: `splitlines(keepends=True)` の挙動。
**事故リスク（低）**: 入力制限あり。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`SequenceMatcher` の autojunk ヒューリスティック（長い系列で頻出要素を junk 扱い）が結果に影響する点は知っておくべき。性能と精度のトレードオフ。

**他フレームワークとの差異**: 標準ライブラリで完結。大規模 diff は専用ライブラリ（`google-diff-match-patch`）を検討。
**nene2 の薄さへの評価**: 薄いラップとして妥当。長さ制限で DoS を防ぐ判断が適切。
**事故リスク（低）**: 入力長制限あり。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `unified_diff` に行リストを渡しているか（文字列直渡しの誤り）。
- `ratio()`/`get_close_matches` の入力長・候補数に上限があるか（O(n²) DoS）。
- `cutoff` が適切か（低すぎるとノイズ）。
- 出力 diff にユーザー入力がそのまま含まれる点（表示側で別途エスケープ — FT229）。

**チームでの安全なパターン**: diff/ratio の入力上限を共通定数化。表示時は HTML エスケープ。
**事故リスク（低）**: 上限をテスト回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 長さ/件数制限・`ValidationException` 変換・`logging` 使用は準拠。O(n²) への入力制限は「リソース消費」防御の一環。
**初心者でも安全な API 達成度**: 行リスト変換・長さ制限を関数内に隠蔽。
**改善提案**: diff 出力を画面表示する場合の「diff + HTML エスケープ（FT229）」の組み合わせを how-to に記載する。
