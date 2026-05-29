# FT264: ast.literal_eval — eval の安全な代替

**日付**: 2026-05-29
**テーマ**: Python `ast.literal_eval` の安全なリテラル評価の実装と検証
**セキュリティ診断**: 🔒 あり（264 % 3 = 0）
**クラッカーペンテスト**: 🔍 あり（264 % 4 = 0）

---

## 概要

`eval`/`exec` は**任意コードを実行**するため CLAUDE.md で禁止。`ast.literal_eval` は **Python リテラル**（str/bytes/数値/tuple/list/dict/set/bool/None）のみを解析し、関数呼び出し・属性アクセス・名前参照を一切評価しない。「文字列から構造化データを取り出したいが eval は使いたくない」場面の安全な代替。診断＋ペンテスト両対象として、eval なら成立する攻撃が全て無効化されることを検証した。

| 危険 | 安全（本 FT） |
|---|---|
| `eval("__import__('os').system('id')")` | `ast.literal_eval`（リテラルのみ） |
| `eval(user_input)` | コード実行の余地なし |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft264-ast-literal-eval/`

| 関数 | 概要 |
|---|---|
| `safe_literal_eval()` | リテラルのみ評価、非リテラルは 422 |
| `_to_jsonable()` | tuple/set/complex/bytes を JSON 可能形へ正規化 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/literal/eval` | リテラルを安全に評価 |

---

## 摩擦点

### F-1: `literal_eval` は名前・呼び出し・属性アクセスを拒否する

**観察**: `eval` は `__import__('os').system(...)`・`open(...).read()`・`().__class__.__bases__[0].__subclasses__()` など任意コードを実行する。`literal_eval` はこれらに `ValueError`/`SyntaxError` を送出（コード実行なし）。条件式・内包表記・lambda も非リテラルとして拒否される。

**対処**: `ast.literal_eval` を使い、例外を 422 に変換。診断で 10 種のコードインジェクションがすべて 422。

### F-2: 結果の正規化（tuple/set/complex/bytes）

**観察**: `literal_eval` は tuple/set/frozenset/complex/bytes も返す。これらは JSON シリアライズできない（complex/bytes）。

**対処**: `_to_jsonable` で tuple/set→list、complex/bytes→repr 文字列に正規化。`(1,2)`→`[1,2]`、`1+2j`→`'(1+2j)'`。

### F-3: 深いネスト・巨大整数の DoS

**観察**: `literal_eval` は内部で `ast.parse` するため、深くネストしたリテラルで `RecursionError`/`MemoryError`、巨大桁整数で int 変換コスト。

**対処**: 入力長を上限化（10k）し、`RecursionError`/`MemoryError` も捕捉。2000 ネストを 3ms で 422、1 万桁整数を 422。

---

## セキュリティ診断 & クラッカーペンテスト

| カテゴリ | ペイロード | 結果 |
|---|---|---|
| import 実行 | `__import__('os').system('id')` | **422** |
| ファイル読取 | `open('/etc/passwd').read()` | **422** |
| subclasses 探索 | `().__class__.__bases__[0].__subclasses__()` | **422** |
| globals/exec | `globals()` / `exec('x=1')` | **422** |
| lambda | `lambda: 1` | **422** |
| 条件式/内包表記 | `1 if True else 2` / `[x for x in range(10)]` | **422** |
| 名前参照 | `os.getcwd()` / `True and __import__('os')` | **422** |
| 正常リテラル | list/dict/tuple/str/float/bool/None/set/bytes/complex | **200** |
| DoS ネスト | 2000 段 | **422 / 3ms** |
| DoS 整数 | 1 万桁 | **422** |
| サイズ | 10k 超 | **422** |

### まとめ

| 攻撃カテゴリ | 試行 | 突破 | 耐えた |
|---|---|---|---|
| コードインジェクション | 10 | 0 | 10 |
| DoS（ネスト/整数/サイズ） | 3 | 0 | 3 |

**総合評価: 合格**

`literal_eval` は構造的にコード実行を行わず、eval なら成立する全攻撃を無効化。`eval` をユーザー入力に使わず `literal_eval`（または json）を使う原則を実証。

---

## テスト結果

```
8 passed in 0.84s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

「文字列を Python の値にしたい」とき `eval` を使いがちだが危険と知れる。`literal_eval` が安全な代替。

**ドキュメント理解**: eval との違いをコメントで明示。
**事故リスク（高）**: ユーザー入力に `eval`。
**規約の使いやすさ**: text → value が分かりやすい。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

設定値や CSV セルの「Python っぽい文字列」を `eval` で変換する事故が多い。`literal_eval` か json に置換すべき。

**コピペ可能性**: safe_literal_eval は流用可。
**拡張時の罠**: eval への回帰・tuple/set の JSON 化。
**事故リスク（高）**: eval による RCE。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS の `eval`/`Function` の危険と同じ。データは JSON.parse、Python では json/literal_eval と理解。

**エラーレスポンスの質**: 非リテラルは 422。
**Python 固有概念**: ast・リテラルの範囲。
**事故リスク（低）**: 構造的に安全。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`eval` は最重要禁止事項。`literal_eval` でも深いネスト DoS はあるため入力制限は必要。基本はデータ交換に json を使う。

**他フレームワークとの差異**: どの言語でも eval は厳禁。
**nene2 の薄さへの評価**: literal_eval + 正規化 + 入力制限の組み合わせが適切。
**事故リスク（低）**: 全攻撃を実測遮断。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `eval`/`exec` をユーザー入力に使っていないか（厳禁）。
- 構造化データは json、Python リテラルなら `literal_eval`。
- 深いネスト・巨大整数・サイズの上限。
- 結果の型（tuple/set/complex/bytes）の扱い。

**チームでの安全なパターン**: データ交換は json、どうしても Python リテラルなら literal_eval + 入力制限。eval を lint で禁止。
**事故リスク（低）**: 全攻撃を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `eval`/`exec` 禁止を実証。`Any` 不使用（`JsonValue`）・Pydantic 制限・`ValidationException` 変換・`logging` 使用も準拠。FT240（安全なデシリアライズ）・FT236/FT248（テンプレート/format）と並ぶ「危険プリミティブ回避」シリーズ。
**初心者でも安全な API 達成度**: literal_eval を採用しコード実行の余地を原理的に排除。
**改善提案**: 「ユーザー入力に eval/exec を使わない（json/literal_eval を使う）」を how-to の危険プリミティブ一覧に追加する。
