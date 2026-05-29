# FT233: textwrap — wrap / fill / shorten / indent

**日付**: 2026-05-29
**テーマ**: Python `textwrap` モジュールのテキスト整形の実装と検証
**セキュリティ診断**: なし（233 % 3 = 2）
**クラッカーペンテスト**: なし（233 % 4 = 1）

---

## 概要

`textwrap` はテキストの折り返し・省略・インデントを提供する。HTTP API でラップし wrap / shorten / indent を検証した。CLI 出力やメール本文整形で頻出のユーティリティ。

| API | ユースケース |
|---|---|
| `textwrap.wrap(text, width)` | width で折り返し行リスト |
| `textwrap.shorten(text, width, placeholder)` | width に収め超過を省略 |
| `textwrap.indent(text, prefix)` | 各行に prefix 付与 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft233-textwrap/`

| 関数 | 概要 |
|---|---|
| `wrap_text()` | `break_long_words=True`（既定）で長語も強制分割 |
| `shorten_text()` | placeholder `" …"` で省略 |
| `indent_text()` | prefix 付与（空行には付けない既定） |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/text/wrap` | 折り返し |
| POST | `/text/shorten` | 省略 |
| POST | `/text/indent` | インデント |

---

## 摩擦点

### F-1: `wrap` の `break_long_words` 既定 True — width 超過の単語も分割される

**観察**: `width` を超える 1 単語（URL や長い識別子など）は、既定（`break_long_words=True`）では**強制的に分割**される。`False` にすると width を超えた行がそのまま残り、レイアウトが崩れる。

**対処**: 既定の `break_long_words=True` を維持し、`x`×20 を width 5 で折っても全行 ≤5 になることをテストで確認。

### F-2: `shorten` は空白を畳んでから width に収める

**観察**: `shorten` は内部で**連続する空白を 1 つに正規化**してから width に収める。元のスペースを保ちたい用途には不向き。また placeholder（既定 `" [...]"`）の長さも width に含まれるため、極端に小さい width だと `ValueError`。

**対処**: placeholder を `" …"` に。短いテキストはそのまま返ることを確認。

### F-3: `indent` は空行に prefix を付けない（既定の predicate）

**観察**: `textwrap.indent(text, prefix)` の既定 predicate は「空白のみの行には prefix を付けない」。意図せず空行に prefix を付けたい場合は predicate を渡す必要がある。

**対処**: 既定挙動（空行は素通り）を採用。`"a\nb"` → `">> a\n>> b"` を確認。

---

## テスト結果

```
7 passed in 0.85s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

折り返し・省略・インデントは直感的。結果が目に見えて変わるので学びやすい。

**ドキュメント理解**: `break_long_words`・`shorten` の空白畳みは説明が要る。
**事故リスク（低）**: 破壊的操作なし。
**規約の使いやすさ**: text + width が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

ログやレポートの整形に便利。`shorten` の空白畳みで「あれ？」となりがち。

**コピペ可能性**: 3 関数とも流用可。
**拡張時の罠**: `shorten` の空白正規化、`indent` の空行スキップ。
**事故リスク（低）**: 入力長・width 制限あり。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

CSS の `text-overflow: ellipsis` に相当する処理をサーバー側でやる感覚。

**エラーレスポンスの質**: width 範囲外は 422。
**Python 固有概念**: `textwrap` の各種オプション。
**事故リスク（低）**: 制限あり。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

CLI ヘルプ生成（argparse FT219 と併用）やメール整形で使う。マルチバイト幅（東アジア文字）は `textwrap` が考慮しない点に注意。

**他フレームワークとの差異**: 全角幅を厳密に扱うなら `wcwidth` 併用が必要。
**nene2 の薄さへの評価**: 薄いラップとして妥当。
**事故リスク（低）**: 制限あり。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `width` に範囲制限があるか（極小 width での `shorten` 例外）。
- `shorten` の空白正規化を理解した上で使っているか。
- 全角文字の表示幅を考慮する必要がないか（`textwrap` は文字数ベース）。
- 入力長上限（巨大テキストの整形コスト）。

**チームでの安全なパターン**: 表示幅が重要な箇所は `wcwidth` 併用を明記。
**事故リスク（低）**: width/長さ制限を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 範囲/長さ制限・`ValidationException` 変換・`logging` 使用は準拠。
**初心者でも安全な API 達成度**: width 範囲・break_long_words を関数内に固定し、行溢れ・例外の余地を抑制。
**改善提案**: 全角幅を扱う場合の `wcwidth` 併用を how-to に補足する。
