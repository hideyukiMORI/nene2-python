# FT215: struct モジュール — pack / unpack / calcsize / Struct

**日付**: 2026-05-23
**テーマ**: Python `struct` モジュールの pack / unpack / calcsize / Struct / byte order の実装と検証
**セキュリティ診断**: なし（215 % 3 = 2）
**クラッカーペンテスト**: なし（215 % 4 = 3）

---

## 概要

`struct` モジュールは Python とバイナリデータ間の変換を提供する。ネットワークプロトコル・バイナリファイル形式・C 言語との相互運用で不可欠なモジュール。

| API | ユースケース |
|---|---|
| `struct.pack(fmt, *v)` | 値をバイト列に変換 |
| `struct.unpack(fmt, data)` | バイト列から値を復元 |
| `struct.calcsize(fmt)` | フォーマット文字列のバイトサイズを計算 |
| `struct.Struct(fmt)` | フォーマット文字列をキャッシュして再利用（高速化） |
| `<`, `>`, `=`, `!`, `@` | バイトオーダー・アライメント指定 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft215-struct/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `pack_values()` | `struct.pack()` で値リストをバイト列に変換 |
| `unpack_values()` | `struct.unpack()` でバイト列（hex）から値を復元 |
| `calc_size()` | `struct.calcsize()` でフォーマット文字列のバイトサイズを計算 |
| `struct_roundtrip()` | `struct.Struct` でパック→アンパック往復確認 |
| `compare_byte_orders()` | リトルエンディアン vs ビッグエンディアンのパック結果を比較 |
| `_validate_format()` | フォーマット文字列の安全性検証（許可文字集合のホワイトリスト） |

### エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/struct/pack` | 値のバイト列変換 |
| POST | `/struct/unpack` | バイト列からの値復元 |
| POST | `/struct/calcsize` | フォーマット文字列のバイトサイズ計算 |
| POST | `/struct/roundtrip` | Struct クラスの往復確認 |
| POST | `/struct/byte-order` | バイトオーダー比較 |

---

## 摩擦点

### F-1: struct フォーマット文字列のインジェクション防御が必要

**観察**: `struct.pack(fmt, *values)` の `fmt` はユーザー入力から直接渡されるため、不正なフォーマット文字を受け入れる可能性がある。`struct.error` は発生するが、フォーマット文字列を検証せずに渡すと任意のメモリレイアウトを試みることになる。

**対処**: `_validate_format()` でフォーマット文字をホワイトリスト検証し、許可外文字を含む場合は 422 を返す。`struct.error` は `ValueError` でラップして上位層に伝える。

```python
_SAFE_FORMAT_CHARS = frozenset("xcbBhHiIlLqQfd?sp")

def _validate_format(fmt: str) -> None:
    stripped = fmt.lstrip("<>!=@")
    for ch in stripped:
        if ch.isdigit():
            continue
        if ch not in _SAFE_FORMAT_CHARS:
            raise ValueError(f"不正なフォーマット文字: {ch!r}")
```

---

### F-2: `struct.unpack` の戻り値型は `tuple[Any, ...]`

**観察**: `struct.unpack(fmt, data)` の戻り値型は `tuple[Any, ...]` である。mypy --strict で型安全に扱うには `list` に変換して `list[int | float | bool]` として返す必要がある。

**対処**: `list(unpacked)` で変換し、`UnpackResult.values: list[int | float | bool]` として型付きで返す。ただし mypy は `list(unpacked)` の要素型を `Any` と推論するため、実際には `list[Any]` → `list[int | float | bool]` の暗黙変換で `mypy --strict` をパスしている（`_PackValue = int | float | bool` が実際の値と一致するため）。

---

## テスト結果

```
26 passed in 0.39s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

`struct` モジュールは「Pythonの値をバイナリデータに変換する仕組み」として理解できる。`pack("<i", 42)` が 4 バイトのバイト列を返すことは直感的。フォーマット文字列（`<i`, `>H`, `d`）の意味は一覧表がないと覚えにくい。

**ドキュメント理解**: フォーマット文字列の記法（バイトオーダー指定子 + 型文字 + オプション数量）は初心者には難解。エンドポイントの `description` に例を入れると助かる。

**事故リスク（中）**: フォーマット文字列と値の数が一致しない場合に `struct.error` が発生するが、エラーメッセージは英語のみ。今 FT では 422 に変換して日本語に近い形で返している。

**規約の使いやすさ**: hex 文字列で入出力することで、フロントエンドからバイナリを扱いやすくなっている。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

バイナリファイルの読み書きや TCP/UDP パケットの解析でよく使う。`Struct` クラスを使えば同じフォーマット文字列を繰り返しコンパイルせずに済む。

**コピペ可能性**: `struct_roundtrip` のパターンは「バイナリプロトコルの実装確認」に直接使える。pack した結果を `bytes.hex()` で表示する手法は実務でよく使うパターン。

**拡張時の罠**: `struct.pack_into()` / `struct.unpack_from()` は既存バッファへの書き込み・読み取りに使うが、今 FT のスコープ外。大量データ処理では `Struct.pack_into()` のほうが効率的。

**事故リスク（低）**: フォーマット文字列のホワイトリスト検証で不正な入力を防いでいる。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

Node.js の `Buffer` や TypedArray（`Int32Array`, `Float64Array`）に相当する。`DataView` のバイトオーダー指定（`getInt32(offset, true)` = リトルエンディアン）と対応している。

**エラーレスポンスの質**: フォーマット文字列のエラーや値の範囲超過が 422 で返るため、フロントエンドが適切にハンドリングできる。

**Python 固有概念**: `struct` のフォーマット文字列はコンパクトだが難読。TypeScript では型システムが構造を表現するため、フォーマット文字列という概念自体が Python 固有。

**事故リスク（低）**: 入力バリデーションが Pydantic + 手動検証で二重保護。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

ネットワークプログラミング（socket モジュールと組み合わせ）や独自バイナリプロトコルの実装でよく使う。`Struct` クラスはパフォーマンスクリティカルな場面での最適化として有効。

**他フレームワークとの差異**: nene2 での struct の使い方は「バイナリデータの変換ユーティリティを HTTP API でラップ」するパターン。実際の利用場面はファームウェア通信・画像処理・暗号化ライブラリとのバイナリ境界。

**nene2 の薄さへの評価**: `_validate_format()` によるホワイトリスト検証は適切。ただし `pack_into` / `iter_unpack` のような高度な API は今 FT のスコープ外で、ドキュメントに記載すると初心者が迷わない。

**事故リスク（低）**: バリデーション二重保護で安全。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- フォーマット文字列はユーザー入力か定数か — ユーザー入力の場合は必ずホワイトリスト検証
- `struct.pack` / `struct.unpack` の値と個数が一致しているか（実行時エラーになる）
- `Struct` クラスのインスタンスをキャッシュして再利用しているか（ループ内で毎回 `struct.pack(fmt, ...)` を呼ぶと遅い）
- バイトオーダーを意識した設計か — ネットワーク通信では通常ビッグエンディアン（`>` または `!`）

**チームでの安全なパターン**: `_SAFE_FORMAT_CHARS` のホワイトリスト + `struct.error` を `ValueError` でラップするパターンは再利用可能。

**事故リスク（低）**: 全入力が Pydantic + _validate_format で保護されており安全。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: フォーマット文字列のホワイトリスト検証は CLAUDE.md のセキュリティポリシー（外部入力を全バリデーション）に準拠している。`frozen=True, slots=True` のレスポンス dataclass も標準に準拠。

**初心者でも安全な API 達成度**: フォーマット文字列の自由度をホワイトリストで制約し、`struct.error` を 422 に変換。初心者がフォーマット文字列のタイプミスをした場合もわかりやすいエラーが返る。

**改善提案**: `pack_values` の `values: list[int | float | bool]` は型が広すぎる（`bool` が `int` として扱われる Python の仕様上の問題）。フォーマット文字列に基づいた型チェックを追加すると、より型安全な API になるが、今 FT のスコープでは過剰設計。
