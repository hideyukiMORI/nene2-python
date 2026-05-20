# FT160: difflib モジュール

**日付**: 2026-05-21
**テーマ**: `difflib` モジュール — SequenceMatcher, get_close_matches, unified_diff, context_diff, HtmlDiff, Differ

---

## 概要

Python 標準ライブラリの `difflib` モジュールを nene2-python フレームワーク上で検証した。
`difflib` はシーケンス比較・差分生成・近似文字列照合に特化したモジュールで、
テキスト差分ツール、スペルチェッカー、バージョン管理ツールなどに活用できる。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft160-difflib/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `similarity_ratio(a, b)` | SequenceMatcher で 0〜1 の類似度を返す |
| `quick_ratio(a, b)` | 高速な近似類似度（上限値） |
| `find_matching_blocks(a, b)` | 一致するブロックのリスト |
| `find_opcodes(a, b)` | 差分操作コード（equal/insert/delete/replace） |
| `find_close_matches(word, possibilities, ...)` | 近似候補（スペルチェック等） |
| `unified_diff_text(a_lines, b_lines)` | unified diff 形式の差分 |
| `context_diff_text(a_lines, b_lines)` | context diff 形式の差分 |
| `differ_diff(a_lines, b_lines)` | Differ クラスの行単位詳細差分 |
| `html_diff(a_text, b_text)` | HtmlDiff によるテーブル形式の HTML 差分 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/diff/ratio` | 2文字列の類似度を計算 |
| POST | `/diff/opcodes` | 差分操作コードを返す |
| POST | `/diff/close-matches` | 近似候補を返す |
| POST | `/diff/unified` | unified diff を返す |
| POST | `/diff/context` | context diff を返す |
| POST | `/diff/differ` | Differ 形式の差分を返す |
| POST | `/diff/html` | HTML diff を返す（`HTMLResponse`） |

---

## テスト結果

```
29 passed in 0.08s
```

テストケース一覧:
- SequenceMatcher: ratio (同一/空/完全不一致/部分一致), quick_ratio, matching_blocks, opcodes (4種)
- get_close_matches: タイポ補完, マッチなし, cutoff 調整, 複数候補
- unified_diff: 変更なし/変更あり/マーカー確認
- context_diff: 変更あり確認
- Differ: 等値/追加/削除行確認
- HTML diff: HTML出力確認
- HTTP エンドポイント: ratio, close-matches, unified, differ, html

---

## 摩擦ポイント

**今回の FT では実装上の摩擦はゼロだった。**

以下は学習上の観察点として記録する。

### 観察1: `unified_diff` は変更なしのとき空文字列を返す

```python
diff = list(difflib.unified_diff(lines, lines))
# → [] (空リスト)
```

変更がない場合はヘッダー行も出力されない。
`"\n".join(diff)` すると空文字列になるため、
「差分なし」を明示的に判別するには `diff == ""` チェックが有効。

### 観察2: `HtmlDiff.make_file()` は完全な HTML ドキュメントを返す

`make_file()` は `<html>`, `<head>`, `<body>` を含む完全な HTML ドキュメントを生成する。
`make_table()` はテーブル断片のみを返す。
FastAPI から返す際は `HTMLResponse` を使い、Content-Type を `text/html` にする必要がある。

### 観察3: `get_close_matches` のデフォルト cutoff は 0.6

`cutoff=0.6` はかなり緩い基準で、明確なタイポ補完には適切。
厳密なマッチが必要な場合（0.9以上）はほとんどの候補が除外される。
用途に応じた `cutoff` チューニングが重要。

### 観察4: `SequenceMatcher` の `autojunk` パラメータ

長いシーケンスでは `autojunk=True`（デフォルト）により、1% 未満の出現頻度の要素を
「ジャンク」として差分計算から除外するヒューリスティックが働く。
短い文字列（10文字以下）では `autojunk` は無効化される。
正確な差分が必要な場合は `SequenceMatcher(None, a, b)` の第1引数に junk 関数を渡すか、
`autojunk=False` を指定する必要がある（`autojunk` は Python 2.7.1+ で追加）。

### 観察5: `Differ` は `?` 行でインラインヒントを付与

```
- hello world
?       ^^^^^
+ hello earth
?       ^^^^^
```

`Differ` は差分がある箇所に `?` で始まるヒント行を挿入する。
テスト・自動処理では `?` 行を除外する必要がある場合がある。

---

## nene2-python フレームワークとの統合

- `ErrorHandlerMiddleware` + `RequestIdMiddleware` は問題なく機能
- `TwoStringsBody`, `CloseMatchBody`, `DiffBody` で入力バリデーション
- `html_diff` エンドポイントのみ `HTMLResponse` を使用（他は `JSONResponse`）

---

## まとめ

`difflib` は純粋に文字列・リスト比較に特化したモジュールで、外部依存なしに
高品質な差分・類似度計算が可能。コードレビューツール、設定ファイル比較、
スペルチェッカーなど幅広い用途に適用できる。摩擦ゼロで実装完了。
