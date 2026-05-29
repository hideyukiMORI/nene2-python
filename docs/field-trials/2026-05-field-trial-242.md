# FT242: heapq — heappush / heappop / nlargest / merge

**日付**: 2026-05-29
**テーマ**: Python `heapq` モジュールのヒープ操作の実装と検証
**セキュリティ診断**: なし（242 % 3 = 2）
**クラッカーペンテスト**: なし（242 % 4 = 2）

---

## 概要

`heapq` はリストを二分ヒープ（min-heap）として扱う関数群を提供する。HTTP API でラップし上位/下位 k 件・ソート済み列の統合・ヒープソートを検証した。`nlargest`/`nsmallest` は全ソートより効率的な top-k 抽出、`merge` は外部マージソートの中核。

| API | ユースケース |
|---|---|
| `heapq.nlargest/nsmallest(k, data)` | 上位/下位 k 件（部分ソート） |
| `heapq.merge(*iterables)` | ソート済み列の遅延統合 |
| `heapq.heapify` + `heappop` | ヒープソート |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft242-heapq/`

| 関数 | 概要 |
|---|---|
| `top_k()` | nlargest/nsmallest で上位・下位 k 件 |
| `merge_sorted()` | ソート済み前提を検証して heapq.merge |
| `heap_sort()` | heapify + heappop で昇順ソート |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/heap/top-k` | 上位・下位 k 件 |
| POST | `/heap/merge` | ソート済み列を統合 |
| POST | `/heap/heapsort` | ヒープソート |

---

## 摩擦点

### F-1: `heapq` は min-heap — 最大値志向は `nlargest` / 符号反転

**観察**: `heapq` は最小ヒープのみ。`heappop` は最小値を返す。最大値優先のキューが欲しい場合は値を符号反転するか `nlargest` を使う。直感（最大ヒープ）と逆。

**対処**: top-k は `nlargest`/`nsmallest` を直接使い、符号反転の手間を避ける。`[5,1,8,3,9,2]` の上位 2 件 = `[9,8]`、下位 2 件 = `[1,2]` を確認。

### F-2: `merge` は各入力がソート済み前提

**観察**: `heapq.merge(*iterables)` は**各イテラブルがソート済み**であることを前提とする（遅延評価）。未ソート入力だと結果が不正になるが例外は出ない（bisect F-1 と同種の silent bug）。

**対処**: 各サブリストの昇順を明示検証し、未ソートは 422。合計点数も上限化。`[[1,4,7],[2,5,8],[3,6,9]]` → `[1..9]` を確認。

### F-3: `nlargest(k, ...)` の k と計算量

**観察**: `nlargest(k, data)` は k が小さいと O(n log k) で効率的だが、k が n に近いと全ソート（O(n log n)）と変わらない。k に上限がないと大きな k で無駄が出る。

**対処**: k を `1〜len(data)` に検証し、データ点数も上限化（DoS 防止）。

---

## テスト結果

```
6 passed in 0.92s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

「上位 k 件」を簡単に取れるのは便利。min-heap であること（最大が欲しいなら nlargest）は最初戸惑う。

**ドキュメント理解**: min-heap 特性をコメントで明示。
**事故リスク（低）**: 計算のみ。
**規約の使いやすさ**: data + k が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

ランキング上位抽出やログのマージで使う。`merge` のソート済み前提は罠。

**コピペ可能性**: top_k/merge_sorted は流用可。
**拡張時の罠**: min-heap の向き・merge の未ソート入力。
**事故リスク（低）**: 前提検証あり。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS に標準ヒープがないのでサーバー側 top-k が便利。

**エラーレスポンスの質**: k 範囲・未ソートは 422。
**Python 固有概念**: min-heap・nlargest。
**事故リスク（低）**: 検証あり。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

優先度付きキューやストリーミング top-k、外部マージソートで使う。大規模なら専用構造や DB を検討。`merge` の遅延評価はメモリ効率的。

**他フレームワークとの差異**: 標準で priority queue を組める。`queue.PriorityQueue` はスレッドセーフ版。
**nene2 の薄さへの評価**: 薄いラップとして妥当。上限・前提検証が良い。
**事故リスク（低）**: 前提・上限あり。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- min-heap 特性を理解し最大優先で符号反転/nlargest を正しく使っているか。
- `merge` の各入力ソート済みを保証/検証しているか（silent bug）。
- k・データ点数・リスト数に上限があるか（DoS）。
- 安定性が要る場合のタプルキー設計（同値の順序）。

**チームでの安全なパターン**: top-k は nlargest、優先度キューはタプル `(priority, seq, item)` で安定化。
**事故リスク（低）**: 前提・上限を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 件数/範囲制限・`ValidationException` 変換・`logging` 使用は準拠。
**初心者でも安全な API 達成度**: min-heap の向き・merge 前提を関数内で吸収/検証し、silent bug を 422 に変換。
**改善提案**: 優先度付きキューの安定化（タプルキー）パターンと `queue.PriorityQueue`（スレッドセーフ）との使い分けを how-to に補足する。
