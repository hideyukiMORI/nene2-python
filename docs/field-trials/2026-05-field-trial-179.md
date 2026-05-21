# FT179: zlib モジュール

**日付**: 2026-05-21
**テーマ**: データ圧縮・解凍・CRC32/Adler-32 整合性検証・展開爆弾対策
**セキュリティ診断**: なし（179 % 3 = 2）

---

## 概要

Python 標準ライブラリの `zlib` モジュールを検証する。
単純な圧縮・解凍にとどまらず、展開爆弾（decompression bomb）対策のストリーミング解凍、
CRC32 と Adler-32 の両チェックサムアルゴリズム、圧縮レベル 1〜9 の比較、
チャンク単位のストリーミング圧縮まで網羅し、Web API での実用的な使い方を検証する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft179-zlib/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `compress(data, level)` | zlib 圧縮（入力 10MB 上限、`CompressResult` 返却） |
| `decompress(compressed_hex)` | hex 文字列から解凍（展開爆弾対策付き） |
| `_decompress_bytes(data)` | ストリーミング解凍コア（50MB 上限をチャンクごとに監視） |
| `decompress_streaming(data)` | raw bytes を受け取る解凍インターフェース |
| `compute_crc32(data)` | CRC32 チェックサム計算（`ChecksumResult` 返却） |
| `compute_adler32(data)` | Adler-32 チェックサム計算（`ChecksumResult` 返却） |
| `verify_crc32(data, expected_hex)` | CRC32 検証 |
| `verify_adler32(data, expected_hex)` | Adler-32 検証 |
| `compare_compression_levels(data)` | レベル 1〜9 の圧縮結果比較（`LevelComparison` リスト） |
| `compress_streaming(chunks, level)` | チャンクリストのストリーミング圧縮 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/compress` | データを zlib 圧縮（`level` 指定可） |
| POST | `/decompress` | zlib 圧縮データを解凍 |
| POST | `/checksum/crc32` | CRC32 チェックサム計算 |
| POST | `/checksum/adler32` | Adler-32 チェックサム計算 |
| POST | `/verify` | チェックサム検証（`algorithm` で切り替え） |
| POST | `/compress/levels` | レベル 1〜9 の圧縮比較 |

---

## テスト結果

**39 passed**（初回から全通過）

```
39 passed in 0.67s
```

mypy: Success / ruff: All checks passed / pip-audit: PYSEC-2025-183（継続監視）

---

## 摩擦ポイント

**今回の FT では実装上の摩擦はゼロだった。**

APIRouter パターン（FT177 F-1 対応）を最初から適用し、テストが一発で全通過した。

---

## 観察点

### 観察1: 展開爆弾（Decompression Bomb）対策にはストリーミング解凍が必須

`zlib.decompress()` は解凍後サイズをチェックする前に全データをメモリに展開する。
ゼロバイト 50MB を level=9 で圧縮すると数百バイトになり、解凍すると 50MB になる。
悪意ある入力をそのまま `decompress()` すると OOM になりえる。

```python
# 危険: 上限チェック前に全解凍
zlib.decompress(huge_compressed_data)  # → OOM の危険

# 安全: ストリーミングでチャンクごとに上限チェック
decompressor = zlib.decompressobj()
total = 0
for offset in range(0, len(data), CHUNK_SIZE):
    chunk = decompressor.decompress(data[offset : offset + CHUNK_SIZE])
    total += len(chunk)
    if total > MAX_OUTPUT_BYTES:
        return None  # 上限超過で早期終了
```

`zlib.decompressobj()` を使うストリーミング方式により、
解凍途中で上限（50MB）を超えたと判断できる。

### 観察2: CRC32 と Adler-32 の使い分け

両者とも `zlib` モジュールに含まれるが特性が異なる。

```python
zlib.crc32(b"hello") & 0xFFFFFFFF  # → 907060870
zlib.adler32(b"hello") & 0xFFFFFFFF  # → 103547413
```

| 特性 | CRC32 | Adler-32 |
|---|---|---|
| 用途 | ファイル整合性（PNG, ZIP, gzip） | zlib ストリームヘッダー |
| 計算速度 | やや遅い | 高速（加算のみ） |
| 小データ衝突耐性 | 高い | 低い（短文字列で衝突しやすい） |
| & 0xFFFFFFFF の必要性 | あり（符号ありの場合がある） | あり |

Web API で「ファイルのダウンロード整合性確認」には CRC32、
「zlib ストリームの内部チェックサム」には Adler-32 が適している。

### 観察3: 圧縮レベルの実効差

繰り返しデータ（`b"hello world! " * 100 = 1300 bytes`）では、
レベル 1〜9 の差は小さいが高圧縮データでは差が出る。

```python
results = compare_compression_levels(b"hello world! " * 100)
# level=1: 34 bytes (ratio=0.0262)
# level=9: 22 bytes (ratio=0.0169)
```

一般的な API ペイロード（JSON 等）ではレベル 6（デフォルト）が
速度と圧縮率のバランス点として適切。

### 観察4: ストリーミング圧縮の結果は oneshot と roundtrip 互換

`zlib.compressobj()` によるストリーミング圧縮の出力は、
`zlib.decompress()` や `zlib.decompressobj()` で正常に解凍できる。
チャンク境界に関係なくストリーム形式は同一なので、
ネットワーク越しの分割送信データをチャンク単位で圧縮してもラウンドトリップが保証される。

```python
chunks = [data[i : i + 64] for i in range(0, len(data), 64)]
streamed = compress_streaming(chunks)
assert decompress_streaming(streamed) == data  # ✅ 常に成立
```

---

## nene2-python フレームワークとの統合

- `compress` / `decompress` エンドポイントは Content-Encoding 圧縮 API の基盤として使える
- `MAX_INPUT_BYTES = 10MB` + Pydantic `max_length=20_971_520`（hex 換算）で DoS 対策済み
- `MAX_OUTPUT_BYTES = 50MB` の展開爆弾対策は、ファイルアップロード API のメモリ安全性に直結
- `verify_crc32` / `verify_adler32` は `hmac.compare_digest` 相当の定数時間比較ではない点に注意
  （チェックサム比較はタイミング攻撃対象にはならないため問題なし）
- `APIRouter` + `create_app()` パターン（FT177 F-1 対応）を最初から適用済み

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

ファイルアップロード API で圧縮ストレージを実装しようとしている。

**ドキュメント理解**: `zlib.compress()` / `zlib.decompress()` のペアは直感的。
圧縮レベルのデフォルト値（6）がなぜ最適なのかは公式ドキュメントに書いていない。  
**事故リスク**: 高。`zlib.decompress()` に信頼できないデータを渡すと OOM になりうる。
`MAX_OUTPUT_BYTES` によるガードを知らずに実装すると本番で問題になる。  
**規約の使いやすさ**: `hex()` / `bytes.fromhex()` の往復は Python 固有概念として最初の壁になる。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

既存の zlib 圧縮コードをコピーして API に組み込もうとしている。

**コピペ可能性**: `compress()` / `decompress()` のラッパーは分かりやすい。
`_decompress_bytes()` の展開爆弾対策ロジックは読んでも「なぜ必要か」が分かりにくい。  
**拡張時の罠**: `MAX_OUTPUT_BYTES` の定数を削除または増やすと展開爆弾に脆弱になる。
「動いているから削ってもいいか」と判断する人がいる。  
**セキュリティ的な事故リスク**: 高。展開爆弾対策なしの実装はサービス停止に直結する。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

TypeScript の `pako`（zlib の JS 実装）に慣れており、Python で同じことをしようとしている。

**エラーレスポンスの質**: 400 Bad Request に具体的なメッセージが返るのは良い。
圧縮爆弾で `None` が返ったときの 400 レスポンスがなぜ「Invalid compressed data」なのかは
クライアント実装側からは分かりにくい（「サイズ上限超過」と区別できない）。  
**Python 固有概念の学習コスト**: `bytes.hex()` / `bytes.fromhex()` の往復は JS にない概念。
`zlib.decompressobj()` のストリーミング API は `pako` の `Inflate` に相当するが設計が異なる。  
**事故リスク**: 低。HTTP 境界での Pydantic バリデーションが充実。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

zlib を直接使うより、HTTP レスポンスの Content-Encoding や S3 のサーバー側圧縮を使うことが多い。

**他フレームワークとの差異**: Django では `GZipMiddleware` が透過的に圧縮するため、
zlib を直接操作するコードは書かない。nene2-python では zlib 操作がアプリコードに露出しており、
ユースケースが明確（ファイルストレージ等）でなければ設計レビューで指摘される。  
**nene2-python の薄さへの評価**: `_decompress_bytes()` の展開爆弾対策ロジックは再利用可能な
ミドルウェア候補。フレームワーク側に `DecompressionSizeLimitMiddleware` として組み込む価値がある。  
**本番投入可能性**: 展開爆弾対策が明示的に実装されており、本番品質として評価できる。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- [x] `zlib.decompress()` を直接呼ばず、ストリーミング解凍で上限チェックをしているか
- [x] `MAX_OUTPUT_BYTES` が `MAX_INPUT_BYTES` より大きいことを確認（圧縮率を考慮）
- [x] `verify_crc32` / `verify_adler32` の比較が文字列の `==` であることの妥当性
  （チェックサム比較はタイミング攻撃対象外なので OK）

**チームでの安全な共有パターン**: `_decompress_bytes()` を内部 API として隠蔽し、
公開 API は `decompress()` と `decompress_streaming()` の 2 つのみに絞った設計が良い。  
**ツール追加の必要性**: `bandit` (ruff S ルール相当) の B322（`zlib.decompress` 直接使用）は
ruff にはないが、コードレビューチェックリストに追加すべき。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 中  
— `zlib.decompress()` 直接使用の罠は `_decompress_bytes()` の命名（アンダースコアで内部実装を示す）で
ある程度ガードできているが、stdlib の `zlib.decompress()` を直接呼ぶと再発する。  
**設計上の負債**: 展開爆弾対策を nene2-python フレームワークの共通ユーティリティとして
`nene2.io.SafeDecompressor` 等に昇格させる価値がある。  
**Follow-up Issue 候補**: なし（現状の実装で十分。フレームワーク統合は別 Issue で検討）

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 低 | `decompress` の 400 エラーメッセージをサイズ超過と不正データで分離する | feat |

---

## まとめ

FT179 では `zlib` モジュールを中心に、データ圧縮・解凍・チェックサム計算を実装した。
39 テストが全通過し、mypy/ruff も問題なし。

最大の発見は展開爆弾（Decompression Bomb）対策の必要性。
`zlib.decompress()` は解凍後サイズを事前チェックできないため、
`zlib.decompressobj()` によるストリーミング解凍でチャンクごとに上限（50MB）を監視する実装が必須。

APIRouter パターン（FT177 F-1 の改善）を最初から適用し、テストが一発で全通過した。

v1.8.50 としてリリース。
