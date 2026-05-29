# FT225: zlib — compress / decompress / crc32（解凍爆弾対策）

**日付**: 2026-05-29
**テーマ**: Python `zlib` モジュールの圧縮・解凍・解凍爆弾対策の実装と検証
**セキュリティ診断**: 🔒 あり（225 % 3 = 0）
**クラッカーペンテスト**: なし（225 % 4 = 1）

---

## 概要

`zlib` は DEFLATE 圧縮の標準モジュール。HTTP API でラップし「テキスト ⇄ zlib 圧縮データ」の往復を検証した。圧縮 API の最大のセキュリティ課題は **解凍爆弾（decompression bomb / zip bomb）** — 数 KB の圧縮データが数 GB に膨張してメモリを枯渇させる攻撃。診断回（225 % 3 = 0）として `decompressobj` + `max_length` による上限付き解凍を中心に検証した。

| API | ユースケース |
|---|---|
| `zlib.compress(data, level)` | DEFLATE 圧縮（レベル 0〜9） |
| `zlib.decompressobj()` + `decompress(data, max_length)` | **上限付き**ストリーム解凍（爆弾対策） |
| `zlib.crc32` | CRC32 チェックサム |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft225-zlib/`

| 関数 | 概要 |
|---|---|
| `compress_text()` | テキストを zlib 圧縮し 16 進・サイズ・crc32 を返す |
| `_safe_decompress()` | `decompressobj` + `max_length` で 1MB 上限の解凍、`unconsumed_tail` で爆弾を検出 |
| `decompress_hex()` | 16 進 zlib データを爆弾対策付きで解凍、UTF-8 検証 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/zlib/compress` | zlib 圧縮（level 指定） |
| POST | `/zlib/decompress` | zlib 解凍（解凍爆弾対策） |

---

## 摩擦点

### F-1: `zlib.decompress(data)` は無制限に展開する — 解凍爆弾の温床

**観察**: ワンショットの `zlib.decompress(data)` は出力サイズに上限がなく、攻撃者が小さな圧縮データ（例: `zlib.compress(b"\x00" * 50_000_000)` は 97KB）を送ると**解凍時に 50MB をメモリに展開**してしまう。増幅率は容易に 1000 倍を超え、メモリ枯渇 DoS になる。

**対処**: `zlib.decompressobj()` を使い `decompress(data, max_length)` で 1 回の出力を上限バイト数に制限する。上限を超える残りは `unconsumed_tail` に残るので、それが非空なら爆弾とみなして拒否する。

```python
decompressor = zlib.decompressobj()
output = decompressor.decompress(data, MAX_DECOMPRESSED_BYTES)
if decompressor.unconsumed_tail:          # 上限超過分が残っている = 爆弾
    raise ValueError("解凍後サイズが上限を超えています（解凍爆弾の疑い）")
output += decompressor.flush()
```

**重要な性質**: この方式は**メモリだけでなく時間も有界**。診断で 50MB 相当の爆弾を **8ms** で拒否できた（全展開せず上限で停止するため）。

### F-2: 圧縮レベルの範囲（0〜9）

**観察**: `zlib.compress(data, level)` の `level` は 0〜9。範囲外は `zlib.error`。ユーザー入力をそのまま渡すと例外になる。

**対処**: Pydantic で `ge=0, le=9`、関数内でも再検証。

### F-3: 解凍成功 ≠ 妥当テキスト

**観察**: 解凍結果が UTF-8 とは限らない（バイナリデータの圧縮など）。

**対処**: `raw.decode("utf-8")` の `UnicodeDecodeError` を捕捉し 422。

---

## セキュリティ診断結果

| # | 攻撃シナリオ | 結果 | 対処 |
|---|---|---|---|
| 1 | 解凍爆弾 2MB / 10MB / 50MB（hex 数 KB〜97KB） | **すべて 422**、最大でも **8ms** で拒否 | `max_length` + `unconsumed_tail`（F-1） |
| 2 | 解凍後 999,999B（上限内） | **200** | 上限内は正常処理 |
| 2 | 解凍後 1,000,001B（上限超過） | **422**（解凍爆弾の疑い） | 境界検証 |
| 3 | 不正 hex / 不正 zlib / 空文字 | 422 / 422 / 200（空→空） | 例外捕捉 |
| 4 | 入力長 DoS（hex 200,001 / text 100,001） | **422**（Pydantic max_length） | 長さ制限 |
| 5 | 非 UTF-8 解凍結果（`\xff\xfe`） | **422** | UTF-8 検証（F-3） |
| 6 | セキュリティヘッダー | 付与あり | ミドルウェア |

**総合評価: 合格**

解凍爆弾を**メモリ・時間ともに有界**に拒否できることを実測で確認（50MB 爆弾を 8ms で遮断）。`zlib.decompress` のワンショット展開を避け、`decompressobj` + `max_length` のストリーム解凍にする設計が決定的に重要。

---

## テスト結果

```
7 passed in 0.95s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

圧縮・解凍の往復は理解しやすい。`compressed_size` と `original_size` の比で圧縮効果が見える。

**ドキュメント理解**: `decompressobj` + `max_length` の爆弾対策は高度。コメントで理由を説明している。
**事故リスク（高）**: `zlib.decompress(user_data)` をそのまま書くと爆弾を食らう。初心者は上限の必要性を知らない。
**規約の使いやすさ**: compress → decompress の往復が素直。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

アップロードファイルやログの圧縮で使う。爆弾対策は知らないと必ず嵌る。

**コピペ可能性**: `_safe_decompress` はそのまま流用できる完成度。
**拡張時の罠**: `decompress(data)`（max_length なし）に戻すと無防備になる。
**事故リスク（高）**: 外部由来の圧縮データをワンショット解凍。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`pako` / `CompressionStream` に対応。ブラウザ側も解凍爆弾の懸念は同じ。

**エラーレスポンスの質**: 爆弾・不正データは 422 Problem Details で明確（`爆弾の疑い` メッセージ）。
**Python 固有概念**: `decompressobj` のストリーミング API。
**事故リスク（低）**: 上限・長さ制限で多層防御。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

解凍爆弾は CVE 多数（HTTP gzip、画像、XML 展開爆弾 FT180 等）の定番。`max_length` ストリーム解凍は王道の対策。

**他フレームワークとの差異**: 多くの HTTP スタックが gzip 展開上限を持つ。アプリ層でも明示的に上限を置くのが堅牢。
**nene2 の薄さへの評価**: 薄いラップに爆弾対策だけ足す設計は妥当。
**事故リスク（低）**: 実測でメモリ・時間有界を確認。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `zlib.decompress(data)` をワンショットで使っていないか — `decompressobj` + `max_length` を使う。
- `unconsumed_tail` で上限超過を検出しているか。
- 解凍後サイズだけでなく**入力サイズ**にも上限があるか（多層）。
- crc32 を認証に使っていないか（FT224 と同じ注意）。
- 解凍結果の UTF-8 検証。

**チームでの安全なパターン**: `_safe_decompress` を共通化し、生 `zlib.decompress` を lint で禁止する。
**事故リスク（低）**: 診断全合格、実測値あり。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 範囲/長さ制限・`ValidationException` 変換・`logging` 使用は準拠。解凍爆弾対策は「リソース消費（OWASP API4:2023）」への明示的防御。
**初心者でも安全な API 達成度**: 爆弾対策を `_safe_decompress` に隠蔽し、初心者がワンショット解凍を書く余地を排除。
**改善提案**: `_safe_decompress`（上限付き解凍）を `nene2` のユーティリティに昇格し、gzip（FT226）・アップロード展開でも再利用する。XML 展開爆弾（FT180 / defusedxml）と並ぶ「展開系の上限」ポリシーとして how-to にまとめる。
