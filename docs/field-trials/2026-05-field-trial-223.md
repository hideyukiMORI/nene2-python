# FT223: base64 — b64encode / urlsafe_b64encode / b64decode / パディング検証

**日付**: 2026-05-29
**テーマ**: Python `base64` モジュールの符号化・復号・厳格デコードの実装と検証
**セキュリティ診断**: なし（223 % 3 = 1）
**クラッカーペンテスト**: なし（223 % 4 = 3）

---

## 概要

`base64` はバイナリを ASCII テキストへ可逆変換する標準モジュール。HTTP API でラップし「テキスト ⇄ base64」の往復と、**厳格デコード（`validate=True`）** による不正入力の拒否を検証した。base64 は「デコードは何でも通る」と誤解されがちだが、`validate=True` を付けないと改行・空白・不正文字を黙って無視してしまう点が実装上の落とし穴。

| API | ユースケース |
|---|---|
| `base64.b64encode` / `b64decode(validate=True)` | 標準 base64 の符号化・厳格復号 |
| `base64.urlsafe_b64encode` / `urlsafe_b64decode` | URL/ファイル名で安全な `-_` variant |
| `str.translate` | URL セーフ `-_` → 標準 `+/` の変換 |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft223-base64/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `encode_text()` | テキストを標準 / URL セーフ両方の base64 で符号化 |
| `decode_text()` | `validate=True` で厳格復号し、UTF-8 でないバイト列は拒否 |
| `_URLSAFE_TO_STD` | `-_` → `+/` の `str.maketrans` 変換表 |

### エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/base64/encode` | 標準 + URL セーフ base64 を返す |
| POST | `/base64/decode` | base64 を厳格復号（urlsafe フラグ対応） |

---

## 摩擦点

### F-1: `b64decode` はデフォルトで不正文字を黙殺する — `validate=True` 必須

**観察**: `base64.b64decode(s)` はデフォルト（`validate=False`）でアルファベット外の文字（改行・空白・記号）を**黙って読み飛ばす**。`"aGVsbG8=\n"` も `"aGV sbG8="` も例外なくデコードされてしまい、不正なトークンを「正常」と誤認するリスクがある（認証トークンの検証などで危険）。

**対処**: `base64.b64decode(data, validate=True)` を使い、アルファベット外の文字があれば `binascii.Error` を送出させ、422 に変換する。改行混じり・記号混じりの base64 が拒否されることをテストで確認。

### F-2: URL セーフ variant には `validate` 引数がない

**観察**: `base64.urlsafe_b64decode()` には `validate` 引数がなく、内部で `-_` を `+/` に変換してから `b64decode`（validate なし）を呼ぶだけ。厳格性を保てない。

**対処**: 自前で `str.translate(_URLSAFE_TO_STD)` で `-_` → `+/` に変換してから `b64decode(..., validate=True)` を通す。URL セーフでも厳格デコードを実現。

### F-3: デコード成功 ≠ 意味のあるテキスト

**観察**: base64 デコードが成功してもバイト列が UTF-8 として妥当とは限らない（`base64.b64encode(b"\xff")` は単独で不正な UTF-8）。

**対処**: `raw.decode("utf-8")` の `UnicodeDecodeError` を捕捉し 422。バイナリ用途なら `byte_length` のみ返す設計にできる。

---

## テスト結果

```
8 passed in 1.02s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

「テキストを base64 にして戻す」流れは理解しやすい。標準と URL セーフの 2 種類が返るので違いを観察できる。

**ドキュメント理解**: `validate=True` の重要性は説明されないと気付けない。コメントが理由を書いている。
**事故リスク（中）**: `b64decode` をデフォルトで使い不正トークンを通す事故をやりがち。
**規約の使いやすさ**: encode → decode の往復が素直。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

API トークンや画像の base64 受け渡しで頻出。URL セーフ variant の扱いが地味に面倒なのを `_URLSAFE_TO_STD` で解決している。

**コピペ可能性**: `decode_text` の厳格デコードはそのまま流用可。
**拡張時の罠**: `urlsafe_b64decode` に validate がないことを知らずに「厳格にしたつもり」になる。
**事故リスク（中）**: 改行混じり base64 の黙殺。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

JS の `atob`/`btoa` と対応。`atob` も不正文字に寛容なので、サーバー側で厳格デコードする価値が分かる。

**エラーレスポンスの質**: 不正 base64・非 UTF-8 は 422 Problem Details で明確。
**Python 固有概念の学習コスト**: `bytes` ⇄ `str` の `.encode()/.decode()` 境界。
**事故リスク（低）**: 長さ制限と厳格デコードで防御。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

`validate=True` を付けるかどうかは経験者でも見落としやすい定番ポイント。JWT 等のトークン検証で特に重要。

**他フレームワークとの差異**: 多くの言語の base64 デコーダは寛容デフォルト。厳格化はアプリ責任。
**nene2 の薄さへの評価**: base64 を薄くラップしつつ、厳格性・UTF-8 検証だけアプリ側に置く設計は妥当。
**事故リスク（低）**: テストで黙殺ケースを回帰化。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- `b64decode` に `validate=True` が付いているか — 不正文字の黙殺防止。
- URL セーフ variant で厳格性を自前担保しているか（`validate` 引数がない）。
- デコード後の UTF-8 検証をしているか — デコード成功 ≠ 妥当テキスト。
- 入力長に上限があるか — 巨大 base64 のメモリ消費。

**チームでの安全なパターン**: `decode_text` を共通化し、トークン検証で寛容デコードを使わせない。
**事故リスク（低）**: 摩擦点が明示され回帰テスト済み。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: Pydantic 長さ制限・`ValidationException` 変換・`logging` 使用は準拠。厳格デコードは「HTTP 境界の全入力を検証」の実践。
**初心者でも安全な API 達成度**: `validate=True` を関数内に隠蔽し、初心者が寛容デコードを書く余地を排除できている。
**改善提案**: `decode_text` の厳格 base64 デコードを `nene2.http` のユーティリティに昇格し、トークン・署名検証で再利用する価値がある。
