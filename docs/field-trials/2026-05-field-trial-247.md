# FT247: operator — itemgetter / 演算子関数の安全なディスパッチ

**日付**: 2026-05-29
**テーマ**: Python `operator` モジュールの関数化演算子の実装と検証
**セキュリティ診断**: なし（247 % 3 = 1）
**クラッカーペンテスト**: なし（247 % 4 = 1）

---

## 概要

`operator` は演算子を関数として提供する（`operator.add` 等）。HTTP API でラップし、`itemgetter` による複数キーソートと、名前指定の二項演算子ディスパッチを検証した。ユーザー入力で演算子名を受ける場合は**許可リスト**が要点（`getattr(operator, name)` で任意属性を呼ばせない）。

| API | ユースケース |
|---|---|
| `operator.itemgetter(*keys)` | dict/シーケンスの複数キー取得（ソートキー） |
| `operator.add/sub/mul/...` | 関数としての演算子 |
| `operator.attrgetter` | 属性取得（**ユーザー入力には使わない**） |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft247-operator/`

| 関数 | 概要 |
|---|---|
| `sort_rows()` | `itemgetter` で複数キーソート、キー存在を検証 |
| `apply_operator()` | 許可リスト（add/sub/mul/truediv/mod）の二項演算子のみ |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/operator/sort` | itemgetter で複数キーソート |
| POST | `/operator/apply` | 許可演算子を適用 |

---

## 摩擦点

### F-1: 演算子名は許可リスト — `getattr(operator, name)` は危険

**観察**: ユーザー入力の演算子名を `getattr(operator, name)` で解決すると、`operator` モジュールの任意属性（`__loader__` など）を呼べてしまう恐れがある。

**対処**: `_BINARY_OPS` 辞書（add/sub/mul/truediv/mod）で**許可リスト**化。`__class__` 等の名前は 422。`getattr` で動的解決しない。

### F-2: `attrgetter` はユーザー入力に使わない（内部属性露出）

**観察**: `operator.attrgetter("x.__class__.__init__")` のようにドット記法で**オブジェクト内部に到達**できる。ユーザー指定キーで `attrgetter` を使うと情報漏洩・攻撃面になる。

**対処**: ソートは `itemgetter`（dict キーのみ）を使い `attrgetter` は使わない。キーは全行存在を検証。

### F-3: `itemgetter` の型混在・キー欠落

**観察**: `sorted(rows, key=itemgetter("k"))` で値の型が混在（int と str）すると `TypeError`。キー欠落も `KeyError`。

**対処**: キー存在を事前検証（422）し、ソート時の `TypeError` を捕捉して「型混在」エラーに変換。

---

## テスト結果

```
6 passed in 0.88s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`itemgetter` で複数キーソートが簡潔に書けるのは便利。許可リストの意味は学ぶ必要。

**ドキュメント理解**: itemgetter/attrgetter の違いと危険性をコメントで明示。
**事故リスク（低）**: 許可リストで防御。
**規約の使いやすさ**: rows + keys が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

テーブルソートや簡易計算 API で使う。`getattr(operator, name)` の誘惑に注意。

**コピペ可能性**: sort_rows/apply_operator は流用可。
**拡張時の罠**: getattr 動的解決・attrgetter 誤用。
**事故リスク（低）**: 許可リスト・itemgetter 限定。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`Array.sort((a,b)=>...)` の comparator に対応。複数キーは tuple で表現される点が Python 的。

**エラーレスポンスの質**: 不正キー・演算子は 422。
**Python 固有概念**: itemgetter のタプル返し。
**事故リスク（低）**: 検証あり。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`sorted(key=itemgetter(...))` は定番。動的演算子・属性アクセスを許可リストで縛る判断は正しい。

**他フレームワークとの差異**: ORM のソートは DB 側。アプリ内ソートで itemgetter。
**nene2 の薄さへの評価**: 薄いラップに許可リストを足す設計が適切。
**事故リスク（低）**: getattr 不使用。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- 演算子・関数名をユーザー入力から `getattr` で解決していないか（許可リスト必須）。
- `attrgetter` をユーザー入力に使っていないか（内部属性露出）。
- ソートキーの存在・型を検証しているか。
- 行数・キー数の上限（DoS）。

**チームでの安全なパターン**: 動的ディスパッチは辞書許可リスト、属性アクセスは itemgetter に限定。
**事故リスク（低）**: 許可リストを回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `Any` 不使用（`JsonValue`）・Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。`getattr` 動的解決を避ける設計は「危険プリミティブ回避」と整合。
**初心者でも安全な API 達成度**: 許可リストと itemgetter 限定で動的解決の余地を排除。
**改善提案**: 「名前 → 関数のディスパッチは辞書許可リスト」を how-to に一般原則として記載する（FT231/FT236/FT240 と同系統）。
