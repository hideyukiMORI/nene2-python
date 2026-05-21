# FT181: gzip モジュール

**日付**: 2026-05-21
**テーマ**: gzip 圧縮・解凍・メタデータ操作・ビルド再現性
**セキュリティ診断**: なし（181 % 3 = 1）

---

## 概要

Python 標準ライブラリの `gzip` モジュールを検証する。
FT179（zlib）との違いを意識しながら、gzip 固有のヘッダーメタデータ（ファイル名・mtime）、
展開爆弾対策付きのストリーミング解凍、mtime=0 による決定論的圧縮（ビルド再現性）まで網羅する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft181-gzip/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `compress(data, filename, level, mtime)` | gzip 圧縮（`CompressResult` 返却） |
| `compress_to_bytes(data, filename, level, mtime)` | gzip 圧縮して raw bytes を返す |
| `decompress(compressed)` | 展開爆弾対策付きストリーミング解凍（`DecompressResult` 返却） |
| `decompress_to_bytes(compressed)` | 解凍して raw bytes を返す |
| `_parse_gzip_header(data)` | gzip ヘッダーからファイル名・mtime を手動解析 |
| `read_gzip_info(compressed)` | メタデータ読み取り（`GzipInfo` 返却） |
| `roundtrip(data, level)` | 圧縮 → 解凍のラウンドトリップ検証 |
| `compress_streaming(chunks, level)` | チャンクリストのストリーミング圧縮 |
| `compress_deterministic(data, level)` | mtime=0 で決定論的圧縮 |
| `is_reproducible(data, level)` | 2 回圧縮して同一バイト列か確認 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/compress` | gzip 圧縮（filename/level 指定可） |
| POST | `/decompress` | gzip 解凍 |
| POST | `/info` | gzip メタデータ読み取り |
| POST | `/roundtrip` | ラウンドトリップ検証 |
| POST | `/compress/streaming` | ストリーミング gzip 圧縮 |
| POST | `/compress/deterministic` | 決定論的圧縮（mtime=0） |

---

## テスト結果

**40 passed**（初回 33 通過 → F-1 修正後 40 全通過）

```
40 passed in 0.60s
```

mypy: Success / ruff: All checks passed / pip-audit: PYSEC-2025-183（継続監視）

---

## 摩擦ポイント

### F-1: `GzipFile.name` は `fileobj=BytesIO` のとき常に空文字列を返す（深刻度: 中）

**事象**: `gzip.GzipFile(filename="test.txt", mode="wb", fileobj=BytesIO())` で
ファイル名を指定して圧縮しても、読み取り時に `gz.name` が `""` を返す。

**原因**: Python の `GzipFile.name` プロパティはファイルシステム上のパスを返す設計。
`fileobj` が `BytesIO` の場合、ディスク上のファイルパスが存在しないため常に空文字列になる。
ファイル名はバイト列として gzip ヘッダーの FNAME フィールドに書き込まれているが、
`gz.name` 経由では取得できない。

**対応**: gzip ヘッダーを直接解析する `_parse_gzip_header()` を実装：
```python
_GZIP_MAGIC = b"\x1f\x8b"
_FEXTRA = 4
_FNAME = 8

def _parse_gzip_header(data: bytes) -> tuple[str, int] | None:
    if len(data) < 10 or data[:2] != _GZIP_MAGIC:
        return None
    flags = data[3]
    mtime = int.from_bytes(data[4:8], "little")
    offset = 10
    if flags & _FEXTRA:
        xlen = int.from_bytes(data[offset:offset+2], "little")
        offset += 2 + xlen
    filename = ""
    if flags & _FNAME:
        end = data.find(b"\x00", offset)
        filename = data[offset:end].decode("latin-1")
    return filename, mtime
```

**副次効果**: 不正な gzip データ（マジックバイト不一致）を早期に拒否できるため、
`read_gzip_info()` の invalid data 検出も正確になった。

---

## 観察点

### 観察1: gzip = zlib + ヘッダーメタデータ

zlib（FT179）との主な違いは gzip ヘッダーの存在。

| 特性 | zlib | gzip |
|---|---|---|
| ファイルフォーマット | raw deflate + zlib wrapper | deflate + gzip header + trailer |
| ファイル名 | なし | FNAME フィールドに格納 |
| mtime | なし | MTIME フィールドに格納 |
| マジックバイト | なし | `\x1f\x8b` |
| 用途 | ネットワーク圧縮・インメモリ | .gz ファイル、HTTP Content-Encoding |

HTTP の `Content-Encoding: gzip` は gzip フォーマット、
`Transfer-Encoding: chunked` と組み合わせるストリーミングは zlib が適している。

### 観察2: mtime=0 でビルド再現性を確保できる

gzip ヘッダーには圧縮時刻（mtime）が埋め込まれる。
mtime がデフォルト（`time.time()`）の場合、同一データでも圧縮のたびにバイト列が変わる。

```python
# 問題: mtime が異なると出力が変わる → Docker イメージのレイヤーハッシュが毎回変わる
buf1 = io.BytesIO()
with gzip.GzipFile(mode="wb", fileobj=buf1, mtime=time.time()) as gz:
    gz.write(data)
# buf1.getvalue() != buf2.getvalue()（別の時刻で生成）

# 解決: mtime=0 で決定論的
with gzip.GzipFile(mode="wb", fileobj=buf, mtime=0.0) as gz:
    gz.write(data)
# 同一データ → 常に同一バイト列
```

Docker イメージビルドや CI でのアーティファクトハッシュ検証に重要。

### 観察3: `GzipFile` の `mode` パラメータは省略できない

```python
# 正: mode を明示
gzip.GzipFile(fileobj=buf, mode="rb")

# 誤: mode 省略 → TypeError または予期しない動作
gzip.GzipFile(fileobj=buf)
```

`open()` とは異なり `mode` のデフォルト値が `"rb"` になっている（Python 3.12 で確認）が、
明示指定するほうが意図が明確で安全。

### 観察4: 展開爆弾対策は zlib と同様にストリーミング読み取りが必須

```python
# 危険: gzip.decompress() は全データをメモリに展開する
gzip.decompress(huge_gzip)  # → OOM の危険

# 安全: チャンク読み取りで MAX_OUTPUT_BYTES を監視
with gzip.GzipFile(fileobj=buf, mode="rb") as gz:
    while True:
        chunk = gz.read(CHUNK_SIZE)
        total += len(chunk)
        if total > MAX_OUTPUT_BYTES:
            return None  # 早期終了
```

---

## nene2-python フレームワークとの統合

- `compress_to_bytes(data, filename="...", mtime=0.0)` はファイルアップロード API のレスポンスに直接使える
- `_parse_gzip_header()` はヘッダー検証のユーティリティとして再利用可能
- `MAX_OUTPUT_BYTES = 50MB` の展開爆弾対策は zlib（FT179）と同じ定数で統一
- Pydantic `max_length=20_971_520` で 10MB のデータ（hex 換算 20MB）まで制限
- `compress_deterministic()` は CI アーティファクトのハッシュ検証に使える

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

API レスポンスのデータを gzip 圧縮して返す機能を実装しようとしている。

**ドキュメント理解**: `gzip.compress()` / `gzip.decompress()` はシンプルで分かりやすい。
`GzipFile` クラスの `filename` / `mtime` パラメータの意味は公式ドキュメントに書いてあるが、
なぜ `gz.name` で取り戻せないかは書いていない（F-1 の罠）。  
**事故リスク**: 高。`gzip.decompress()` に信頼できないデータを渡すと OOM になりうる。
（zlib FT179 と同じリスク）  
**規約の使いやすさ**: `gzip.open()` は通常のファイル操作に慣れた人には直感的。
`io.BytesIO` との組み合わせはやや初心者にはハードルがある。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

既存の gzip ファイル処理コードをコピーして API に組み込もうとしている。

**コピペ可能性**: `gzip.compress()` / `gzip.decompress()` はスクリプト系コードにもよく登場するが、
展開爆弾対策を含むパターンは少ない。コピペ元次第でセキュリティが変わる。  
**拡張時の罠**: `compress_to_bytes()` の `mtime=0.0` のデフォルトを削除すると
ビルド再現性が失われるが、エラーは出ない。「意味があるから付けてある」と分かりにくい。  
**セキュリティ的な事故リスク**: 高。展開爆弾対策なしは DoS に直結。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

フロントエンドから `.gz` ファイルを送信するアップロード API を実装している。

**エラーレスポンスの質**: 不正な gzip データに 400 を返す設計は良い。
`gzip.BadGzipFile` を catch して適切なエラーメッセージを返すことで、
クライアント側でのデバッグが容易。  
**Python 固有概念の学習コスト**: `io.BytesIO` を使ったインメモリ gzip 操作は、
JS の `Blob` / `ArrayBuffer` に慣れた人には少し概念が違う。  
**事故リスク**: 低。HTTP 境界での Pydantic バリデーションが充実。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

HTTP レスポンスの `Content-Encoding: gzip` や静的ファイルの事前圧縮を検討している。

**他フレームワークとの差異**: Django の `GZipMiddleware` は透過的に圧縮するため、
gzip を手動で操作することは少ない。FastAPI でも `GZipMiddleware` が利用可能。
ただし事前圧縮（pre-compressed static files）や S3 アップロード前圧縮には直接操作が必要。  
**nene2-python の薄さへの評価**: `compress_deterministic()` の mtime=0 パターンは
CI/CD パイプラインでよく使うが、stdlib ドキュメントには目立たない。
フレームワーク側で「ビルド再現性のある圧縮」を推奨パターンとして提示する価値がある。  
**本番投入可能性**: 展開爆弾対策 + ヘッダー手動解析は本番品質。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- [x] `gzip.decompress()` 直接使用でなく、ストリーミング解凍で上限チェックがあるか
- [x] `gz.name` でファイル名を取得しようとして空文字列を返すコードがないか（F-1）
- [x] `mtime` が指定されていないコードが「毎回違うバイト列」を生成していないか

**チームでの安全なパターン**: `compress_to_bytes(data, mtime=0.0)` を社内標準として
「再現可能圧縮はこれを使う」とドキュメント化することで、mtime の罠を全員が回避できる。  
**ツール追加の必要性**: bandit B301 相当（`gzip.decompress` 直接使用）を
コードレビューチェックリストに追加すべき。ruff には相当ルールなし。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 中  
— `gzip.decompress()` 直接使用の罠は FT179 と同じ。
zlib と gzip で同じ問題が繰り返されることは「stdlib の設計の一貫性のなさ」を示している。  
**設計上の負債**: `_parse_gzip_header()` はプライベートだが、
gzip ヘッダーを扱う他のコードでも必要になりうる。
`nene2.io.gzip` モジュールとして昇格させる候補。  
**Follow-up Issue 候補**: なし（現状の実装で十分）

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 低 | `GzipFile.name` が BytesIO で空になる挙動を How-to ドキュメントに記載 | docs |

---

## まとめ

FT181 では `gzip` モジュールを中心に、圧縮・解凍・メタデータ操作・ビルド再現性を実装した。
40 テストが全通過し、mypy/ruff も問題なし。

最大の発見は F-1: `GzipFile.name` が `fileobj=BytesIO` のとき常に空文字列を返す問題。
gzip ヘッダーのファイル名フィールドを取得するには、バイト列を直接解析する `_parse_gzip_header()` が必要。
この発見により、不正な gzip データの早期検出も正確になった。

`mtime=0.0` による決定論的圧縮は Docker イメージビルドや CI での
アーティファクトハッシュ検証に重要な知見。

v1.8.52 としてリリース。
