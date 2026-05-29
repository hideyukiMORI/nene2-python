# FT254: queue — Queue / LifoQueue / PriorityQueue

**日付**: 2026-05-29
**テーマ**: Python `queue` モジュールのキュー構造の実装と検証
**セキュリティ診断**: なし（254 % 3 = 2）
**クラッカーペンテスト**: なし（254 % 4 = 2）

---

## 概要

`queue` はスレッドセーフなキュー（FIFO/LIFO/優先度）を提供する。HTTP API でラップし取り出し順を検証した。`PriorityQueue` の **`(priority, seq, item)` 安定化パターン**が要点 — 優先度同値でアイテム本体を比較すると比較不能型で `TypeError` になる。

| API | 性質 |
|---|---|
| `queue.Queue` | FIFO |
| `queue.LifoQueue` | LIFO（スタック） |
| `queue.PriorityQueue` | 優先度順（最小ヒープ） |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft254-queue/`

| 関数 | 概要 |
|---|---|
| `drain_fifo()` / `drain_lifo()` | FIFO / LIFO 取り出し |
| `drain_priority()` | `(priority, seq, value)` で安定優先度順 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/queue/fifo` | FIFO |
| POST | `/queue/lifo` | LIFO |
| POST | `/queue/priority` | 優先度順 |

---

## 摩擦点

### F-1: `PriorityQueue` は `(priority, seq, item)` で安定化する

**観察**: `PriorityQueue` は要素をタプル比較する。`(priority, item)` を入れると priority 同値時に `item` を比較し、`item` が dict 等の**比較不能型だと `TypeError`**。また安定性（投入順）も保証されない。

**対処**: `(priority, seq, value)` の 3 要素タプルにし、`seq`（投入連番）で同値時の比較を決定する。`value` は比較されない。同 priority で投入順を維持（`["first","second"]`）を確認。

### F-2: `queue` はスレッドセーフ（`collections.deque` との違い）

**観察**: `queue.Queue` はロックを内蔵しスレッド間の生産者/消費者に安全。単一スレッドの軽量用途では `collections.deque`（FT207）の方が高速。

**対処**: 用途で選択。マルチスレッドのワーカーキューは `queue`、単純な両端キューは `deque`。

### F-3: `get()` のブロッキングと `maxsize`

**観察**: 空キューへの `get()` は既定でブロックし、`maxsize` 到達時の `put()` もブロックする。バッチ処理では `qsize()` 回だけ取り出すか `get_nowait()` を使う。

**対処**: 本 FT は投入数だけ `get()` する（ブロックしない）。リクエスト処理ではブロッキング get を避ける。

---

## テスト結果

```
5 passed in 0.86s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

FIFO/LIFO は直感的。優先度キューの安定化タプルは高度だが結果で納得できる。

**ドキュメント理解**: (priority, seq, item) の理由をコメントで明示。
**事故リスク（低）**: バッチでは破壊性なし。
**規約の使いやすさ**: items → order が明快。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

ジョブキューやタスク優先度で使う。PriorityQueue に dict を直接入れて TypeError を踏みやすい。

**コピペ可能性**: drain_priority の安定化は流用価値大。
**拡張時の罠**: (priority, item) 直入れ・ブロッキング get。
**事故リスク（低）**: seq 安定化で回避。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS に標準キューはなく配列で代用。優先度キューの概念が新鮮。

**エラーレスポンスの質**: 空・超過は 422。
**Python 固有概念**: PriorityQueue のタプル比較。
**事故リスク（低）**: 検証あり。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

スレッド間ワーカーは queue、async は asyncio.Queue、分散は Redis/RabbitMQ と使い分け。安定化タプルは定石。

**他フレームワークとの差異**: async コンテキストでは asyncio.Queue。
**nene2 の薄さへの評価**: 安定化パターンを組み込んだ設計が良い。
**事故リスク（低）**: seq 安定化。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- PriorityQueue に `(priority, seq, item)` の安定化タプルを使っているか（TypeError・順序）。
- リクエストパスでブロッキング `get()`/`put()` を使っていないか（デッドロック・ハング）。
- スレッドセーフが必要か（queue）単一スレッドか（deque）。
- 件数上限（DoS）。

**チームでの安全なパターン**: 優先度キューは安定化タプル、HTTP では非ブロッキング、用途で queue/deque/asyncio.Queue を選択。
**事故リスク（低）**: 安定化・上限を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。
**初心者でも安全な API 達成度**: 安定化タプルを関数内に隠蔽し TypeError・順序不定の余地を排除。
**改善提案**: queue / deque（FT207）/ asyncio.Queue / heapq（FT242）の使い分け表を how-to に用意する。
