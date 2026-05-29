# FT268: lzma — compress / decompress（解凍爆弾対策）

**日付**: 2026-05-29
**テーマ**: Python `lzma` モジュールの圧縮・解凍と解凍爆弾対策の実装と検証
**セキュリティ診断**: なし（268 % 3 = 1）
**クラッカーペンテスト**: 🔍 あり（268 % 4 = 0）

---

## 概要

`lzma`（XZ/LZMA）は**非常に高い圧縮率**を持つ。それゆえ解凍爆弾の威力も大きい — 数十 KB の lzma データが数百 MB に展開される。FT225（zlib）/FT226（gzip）の解凍上限パターンを lzma に適用し、ペンテストで爆弾を攻撃した。

| API | ユースケース |
|---|---|
| `lzma.compress(data)` | LZMA 圧縮 |
| `lzma.LZMADecompressor()` + `decompress(data, max_length)` | 上限付き解凍 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft268-lzma/`

| 関数 | 概要 |
|---|---|
| `compress_text()` | テキストを lzma 圧縮 |
| `_safe_decompress()` | `LZMADecompressor` + `max_length` で上限超過を拒否 |
| `decompress_hex()` | 16 進 lzma を爆弾対策付きで解凍、UTF-8 検証 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/lzma/compress` | lzma 圧縮 |
| POST | `/lzma/decompress` | lzma 解凍（爆弾対策） |

---

## 摩擦点

### F-1: lzma は高圧縮ゆえ解凍爆弾の威力が大きい

**観察**: `lzma.compress(b"\x00" * 200_000_000)` は **約 58KB**（hex）にしかならない。これを `lzma.decompress`（ワンショット）すると 200MB をメモリ展開する。zlib/gzip より圧縮率が高いぶん危険。

**対処**: `lzma.LZMADecompressor()` + `decompress(data, max_length=MAX+1)` で 1 回の出力を上限化。上限超過分が出たら爆弾として拒否。診断で 200MB 爆弾を **6ms** で 422（メモリは MAX+1 に有界）。

### F-2: 例外型は `lzma.LZMAError`

**観察**: 不正な lzma データは `lzma.LZMAError`（zlib の `zlib.error`、gzip の `OSError` と異なる）。

**対処**: `except lzma.LZMAError` で捕捉し 422。

### F-3: 解凍結果の UTF-8 検証

**観察**: 解凍結果がテキストとは限らない。

**対処**: `raw.decode("utf-8")` の `UnicodeDecodeError` を捕捉。バイナリ用途なら byte_length のみ返す。

---

## クラッカーペンテスト

### フェーズ1: 構造推測

`/lzma/decompress` から lzma 解凍と推測。高圧縮ゆえの爆弾を狙う。

### フェーズ2: 攻撃実行ログ

| カテゴリ | ペイロード | 結果 |
|---|---|---|
| 爆弾 2MB | hex 832B | **422 / 28ms** |
| 爆弾 50MB | hex 14.8KB | **422 / 5ms** |
| 爆弾 200MB | hex 58KB | **422 / 6ms**（メモリ有界） |
| 境界 999,999B | 上限内 | **200** |
| 境界 1,000,001B | 上限超過 | **422** |
| 不正 lzma | `deadbeef` | **422** |
| 不正 hex | `zz` | **422** |
| 入力長 DoS | hex 200k+1 | **422** |

### フェーズ3: まとめ

| 攻撃カテゴリ | 試行 | 突破 | 耐えた |
|---|---|---|---|
| 解凍爆弾 | 3 | 0 | 3 |
| 境界 | 2 | 0 | 2 |
| 不正/DoS | 3 | 0 | 3 |

**攻撃耐性評価**: 堅牢
**発見した弱点**: なし。`max_length` 解凍でメモリ・時間ともに有界（200MB 爆弾を 6ms で遮断）。

---

## テスト結果

```
5 passed in 0.95s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

zlib/gzip と同じ使い勝手。lzma が特に高圧縮で爆弾が危険と知れる。

**ドキュメント理解**: max_length 解凍をコメントで明示。
**事故リスク（高）**: `lzma.decompress` をそのまま使い爆弾を食らう。
**規約の使いやすさ**: compress/decompress の往復が素直。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

.xz ファイルの処理で使う。ワンショット解凍の罠は zlib/gzip と同じ。

**コピペ可能性**: `_safe_decompress` は流用可。
**拡張時の罠**: `lzma.decompress` への回帰・例外型 LZMAError。
**事故リスク（高）**: 高圧縮ゆえの爆弾。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

XZ は配布物でお馴染み。サーバー側の解凍上限の重要性が分かる。

**エラーレスポンスの質**: 爆弾・不正は 422。
**Python 固有概念**: LZMADecompressor のストリーム API。
**事故リスク（低）**: 上限あり。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

圧縮形式横断で「解凍は必ず上限付き」が鉄則。lzma は圧縮率が高いぶん上限が特に重要。

**他フレームワークとの差異**: zlib/gzip/lzma/bz2 すべて同じ規律。
**nene2 の薄さへの評価**: FT225/226 と一貫した上限付き解凍。
**事故リスク（低）**: 実測で有界。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `lzma.decompress` ワンショットを避け `LZMADecompressor` + `max_length` か。
- 例外型（LZMAError）を正しく捕捉しているか。
- 入力サイズ・解凍後サイズの二重上限。
- UTF-8 検証。

**チームでの安全なパターン**: 圧縮形式横断で共通の上限付き解凍ユーティリティ。
**事故リスク（低）**: 爆弾を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。「展開系の上限」ポリシー（FT225/226/260）の継続。
**初心者でも安全な API 達成度**: max_length 解凍を関数内に隠蔽し、ワンショット解凍の罠を排除。
**改善提案**: zlib/gzip/lzma/bz2 を束ねた「上限付き解凍」共通ユーティリティを `nene2` に提供する。
