# FT226: gzip — compress / decompress / GzipFile（解凍上限）

**日付**: 2026-05-29
**テーマ**: Python `gzip` モジュールの圧縮・解凍の実装と検証
**セキュリティ診断**: なし（226 % 3 = 1）
**クラッカーペンテスト**: なし（226 % 4 = 2）

---

## 概要

`gzip` は gzip フォーマット（DEFLATE + ヘッダ/CRC）の標準モジュール。FT225（zlib）の解凍上限パターンを gzip 形式に適用し、加えて **`mtime` による出力の非決定性**という gzip 固有の落とし穴を検証した。

| API | ユースケース |
|---|---|
| `gzip.compress(data, mtime=0)` | gzip 圧縮（mtime 固定で決定的出力） |
| `gzip.GzipFile(fileobj=...)` + `read(n)` | ストリーム解凍（上限付き読み） |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft226-gzip/`

| 関数 | 概要 |
|---|---|
| `compress_text()` | `mtime=0` 指定で決定的な gzip 圧縮 |
| `_safe_gunzip()` | `GzipFile.read(MAX+1)` で解凍後サイズを有界化、超過なら拒否 |
| `decompress_hex()` | 16 進 gzip を解凍上限付きで復号、UTF-8 検証 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/gzip/compress` | gzip 圧縮 |
| POST | `/gzip/decompress` | gzip 解凍（上限付き） |

---

## 摩擦点

### F-1: `gzip.compress` はデフォルトで現在時刻（mtime）を埋め込み出力が非決定的になる

**観察**: `gzip.compress(data)` は gzip ヘッダに**現在時刻の mtime** を書き込む。そのため同じ入力でも実行のたびに出力が変わり、ハッシュ照合・キャッシュキー・スナップショットテストが壊れる。

**対処**: `gzip.compress(data, mtime=0)` で mtime を固定し、決定的な出力にする。テスト `test_output_is_deterministic` で同一入力 → 同一出力を確認。

### F-2: gzip の解凍上限は `GzipFile.read(n)` で有界化する

**観察**: `gzip.decompress(data)` はワンショットで無制限展開（FT225 と同じ解凍爆弾リスク）。zlib の `decompressobj` のような `max_length` 引数はない。

**対処**: `gzip.GzipFile(fileobj=BytesIO(data)).read(MAX+1)` でストリーム読みし、上限 +1 バイトだけ読んで超過を検出する。読み込みがストリーミングのためメモリは ~MAX+1 に有界。2MB 爆弾を 422 で拒否（`test_decompression_bomb_rejected`）。

### F-3: 不正データの例外は `OSError` / `EOFError`

**観察**: gzip は不正なマジックバイト・途中切れデータに対し `zlib.error` ではなく `OSError`（`BadGzipFile` は `OSError` サブクラス）や `EOFError` を送出する。zlib（FT225）と例外型が異なる。

**対処**: `except (OSError, EOFError)` で捕捉し `ValueError` → 422。

---

## テスト結果

```
6 passed in 1.05s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

zlib（FT225）とほぼ同じ使い勝手。`mtime=0` の必要性は説明されないと気付けない。

**ドキュメント理解**: 「同じ入力なのに出力が毎回違う」現象は混乱の元。コメントが理由を書いている。
**事故リスク（中）**: 解凍上限を付け忘れる。`mtime` 非決定性でテストが不安定になる。
**規約の使いやすさ**: compress → decompress の往復は素直。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

ログの gzip 配信やバックアップで使う。`mtime=0` の罠は実務でキャッシュ不整合として現れる。

**コピペ可能性**: `_safe_gunzip` の上限付き読みは流用可。
**拡張時の罠**: `gzip.decompress` に戻すと無防備。例外型が OSError 系で zlib と違う。
**事故リスク（中）**: 解凍爆弾・mtime 非決定性。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

HTTP の `Content-Encoding: gzip` でお馴染み。サーバー側の解凍上限の重要性が分かる。

**エラーレスポンスの質**: 不正データ・爆弾は 422 Problem Details で明確。
**Python 固有概念**: `GzipFile` のファイルライクなストリーム API。
**事故リスク（低）**: 上限・長さ制限で防御。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`mtime=0` は再現ビルド・ETag 安定化で重要。解凍上限は zlib と同じ規律。

**他フレームワークとの差異**: gzip 形式はヘッダ/CRC を持つぶん zlib より頑健だが解凍爆弾耐性は同じくアプリ責任。
**nene2 の薄さへの評価**: 薄いラップに上限と決定性を足す設計は妥当。
**事故リスク（低）**: 爆弾テスト回帰化。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `gzip.compress` に `mtime=0` を指定しているか — 出力の決定性。
- `gzip.decompress` ワンショットを避け `GzipFile.read(上限+1)` で有界化しているか。
- 例外捕捉が `OSError`/`EOFError`（gzip 固有）になっているか。
- 入力長上限・UTF-8 検証。

**チームでの安全なパターン**: zlib/gzip 双方の上限付き解凍を共通ユーティリティ化。
**事故リスク（低）**: 摩擦点が回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 長さ制限・`ValidationException` 変換・`logging` 使用は準拠。解凍上限は「リソース消費」防御の継続。
**初心者でも安全な API 達成度**: `mtime=0` と上限付き解凍を関数内に隠蔽。
**改善提案**: FT225（zlib）と共通の「展開系上限」ユーティリティを `nene2` に用意し、gzip/zlib/XML（FT180）を横断的に守る。
