# FT222: hashlib — sha256 / pbkdf2_hmac / blake2 / compare_digest

**日付**: 2026-05-29
**テーマ**: Python `hashlib` モジュールのハッシュ計算・パスワードハッシュ・定数時間比較の実装と検証
**セキュリティ診断**: 🔒 あり（222 % 3 = 0）
**クラッカーペンテスト**: なし（222 % 4 = 2）

---

## 概要

`hashlib` はハッシュアルゴリズムの標準モジュール。HTTP API でラップし「整合性ハッシュ」と「パスワードハッシュ＋検証」を検証した。ハッシュは ① 弱アルゴリズム（md5/sha1）の誤用、② パスワードを生ハッシュで保存、③ タイミング攻撃（`==` 比較）という 3 大事故を招きやすく、セキュリティ診断回（222 % 3 = 0）の題材として最適。

| API | ユースケース |
|---|---|
| `hashlib.new(algo, data)` | 内容ハッシュ（整合性検証）。アルゴリズムはホワイトリスト制 |
| `hashlib.pbkdf2_hmac("sha256", pw, salt, iters)` | パスワードハッシュ（ソルト + 高反復） |
| `secrets.token_bytes()` | 予測不可能なソルト生成 |
| `hmac.compare_digest(a, b)` | 定数時間比較（タイミング攻撃対策） |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft222-hashlib/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `compute_digest()` | ホワイトリスト（sha256 / sha512 / blake2b）の強アルゴリズムで内容ハッシュを計算 |
| `hash_password()` | `pbkdf2_hmac` + `secrets` ソルト + 600,000 反復でパスワードハッシュを生成 |
| `verify_password()` | `hmac.compare_digest` で定数時間検証。iterations 上限で DoS を防ぐ |
| `_validate_length()` | content / password の長さ制限 |

### エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/hash/digest` | 内容ハッシュを計算（algorithm 指定可） |
| POST | `/hash/password` | パスワードをハッシュ化（salt / iterations を返す） |
| POST | `/hash/verify` | パスワードを定数時間検証 |

---

## 摩擦点

### F-1: パスワード用途では生ハッシュ（sha256）ではなく `pbkdf2_hmac` を使う

**観察**: `hashlib.sha256(password)` は高速すぎて、GPU で毎秒数十億回試行できるため**パスワード保存に使ってはいけない**。だが API 名が同じ `hashlib` のため初心者は `sha256` でパスワードを保存しがち。

**対処**: パスワードは必ず `hashlib.pbkdf2_hmac("sha256", pw, salt, iterations)` を使う。`iterations` は OWASP 2023 推奨の **600,000**（PBKDF2-HMAC-SHA256）、ソルトは `secrets.token_bytes(16)` で生成。同じパスワードでも毎回ソルトが異なるため出力が変わる（テスト `test_salt_is_random_per_call` で確認）。

```python
salt = secrets.token_bytes(SALT_BYTES)
derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
```

---

### F-2: パスワード照合は `==` ではなく `hmac.compare_digest`（タイミング攻撃）

**観察**: ハッシュの一致判定を `derived == expected` で書くと、Python の文字列/バイト比較は**先頭から逐次比較して不一致で早期 return** するため、一致するバイト数に応じて応答時間が変わる。攻撃者はこの差を統計的に観測してハッシュを 1 バイトずつ特定できる（タイミング攻撃）。

**対処**: `hmac.compare_digest(derived, expected)` を使う。入力長に依存しない定数時間で比較し、長さが異なっても例外を出さず `False` を返す（診断 #6 で確認）。

```python
valid = hmac.compare_digest(derived, expected)  # == は使わない
```

---

### F-3: `hashlib.new(name)` は md5 / sha1 も受け付ける — ホワイトリスト必須

**観察**: `hashlib.new("md5")` も `hashlib.new("sha1")` も成功する。アルゴリズム名をユーザー入力からそのまま渡すと、衝突耐性のない弱アルゴリズムを選ばせられる。`hashlib.algorithms_guaranteed` には `md5` `sha1` が含まれる。

**対処**: `ALLOWED_DIGEST_ALGORITHMS = ("sha256", "sha512", "blake2b")` のホワイトリストで検証し、それ以外は 422。診断 #1 で `md5` / `sha1` / `MD5`（大文字）/ `sha224` / `../sha256` すべて遮断を確認。

---

## セキュリティ診断結果

| # | 攻撃シナリオ | 結果 | 対処 |
|---|---|---|---|
| 1 | 弱アルゴリズム誤用（`md5` / `sha1` / `MD5` / `sha224` / `../sha256`） | すべて **422** | ホワイトリスト（F-3） |
| 2 | パスワードハッシュ強度 | `pbkdf2_sha256` / **600,000 反復** / 16 byte ソルト | OWASP 2023 準拠（F-1） |
| 3 | DoS: 過大 iterations（10,000,000） | **422**（Pydantic `le=600000`） | iterations 上限 |
| 3 | DoS: iterations=0 / -5 | **422**（Pydantic `ge=1`） | 下限検証 |
| 3 | DoS: content 100,001 文字 | **422**（`max_length`） | 長さ制限 |
| 4 | 不正 hex（奇数長 `abc` / 非 hex `zz...`） | **422** Problem Details | `bytes.fromhex` の例外を捕捉 |
| 5 | タイミング攻撃 | `hmac.compare_digest` 使用を確認 | F-2 |
| 6 | 異なる長さの保存ハッシュで照合 | **200** `{valid: false}`（例外漏れなし） | compare_digest が安全に False |
| 7 | セキュリティヘッダー | `X-Content-Type-Options` / `X-Frame-Options` / `X-Request-Id` 付与 | ミドルウェア |

**総合評価: 合格**

弱アルゴリズムのホワイトリスト遮断・OWASP 準拠のパスワードハッシュ・定数時間比較・iterations 上限による DoS 防止がすべて機能。コードレビュー時の唯一の注意点として、ソース中の `==` 文字列は**コメント（`# == ではなく定数時間比較`）のみ**で、実比較は `compare_digest` であることを確認した（自動 grep の誤検知に注意）。

---

## テスト結果

```
11 passed in 3.27s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。
（実行時間の大半は 600,000 反復の pbkdf2 × 複数テスト。OpenSSL 実装のため許容範囲。）

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

「ハッシュ＝パスワードを安全にする魔法」と思いがちだが、`sha256` と `pbkdf2_hmac` の使い分けがこの FT の肝。エンドポイントが `/digest`（整合性用）と `/password`（パスワード用）で分かれているので役割の違いに気付ける。

**ドキュメント理解**: ソルトや反復回数の意味は最初わからないが、レスポンスに `iterations` / `salt_hex` が出るので「何が保存されるか」が見える。
**事故リスク（高）**: `hashlib.sha256(password)` でパスワードを保存する事故をやりがち。`/digest` と `/password` の分離が抑止になる。
**規約の使いやすさ**: `password` を送ると salt / iterations / hash が返り、それをそのまま `/verify` に渡せる往復が直感的。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

ログイン機能を自作するときに踏みやすい地雷（生ハッシュ・`==` 比較）が一通り対策されている。`hash_password` / `verify_password` はコピペで使える。

**コピペ可能性**: pbkdf2 + secrets ソルト + compare_digest の3点セットはそのまま流用できる。
**拡張時の罠**: `verify` で受け取った `iterations` を無検証で pbkdf2 に渡すと過大値で CPU を焼かれる。上限チェック（`le=600000`）が必須。
**事故リスク（中）**: アルゴリズム名をユーザー入力から取る設計だと md5 を選ばれる。ホワイトリスト必須。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`crypto.subtle.digest` の感覚に近い。パスワードハッシュをサーバー側でやる理由（クライアント送信前ハッシュは無意味）を理解する契機になる。

**エラーレスポンスの質**: 不正 hex・弱アルゴリズムは 422 Problem Details で `{field, message, code}` が返り、フロントで扱いやすい。
**Python 固有概念の学習コスト**: `bytes` と `str` の境界（`.encode()` / `.hex()` / `bytes.fromhex`）は JS の文字列一辺倒に慣れていると戸惑う。
**事故リスク（低）**: 入力は Pydantic と長さ制限で防御。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `PBKDF2PasswordHasher`（デフォルト 600,000 反復前後）と同じ設計。`compare_digest` の使用も標準。`bcrypt`/`argon2` を使わない場合の pbkdf2 ベースラインとして妥当。

**他フレームワークとの差異**: Django は `make_password` / `check_password` でこれを隠蔽している。本 FT は素の `hashlib` で同等を組む「中身」を示せている。
**nene2 の薄さへの評価**: hashlib を薄くラップしつつ、ホワイトリスト・iterations 上限というセキュリティ判断だけアプリ側に置く設計は適切。
**事故リスク（低）**: セキュリティ診断全合格。argon2 への移行余地はコメントで触れる価値あり。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- パスワードに生ハッシュ（`sha256`/`md5`）を使っていないか — `pbkdf2_hmac` / `bcrypt` / `argon2` を使う。
- ハッシュ照合が `==` ではなく `hmac.compare_digest` か — タイミング攻撃。`==` の grep は**コメント誤検知**に注意。
- ソルトが `secrets`（`random` ではない）由来か・リクエストごとにユニークか。
- `iterations` に上限があるか — 過大値による CPU DoS。
- アルゴリズム名をユーザー入力から取る場合ホワイトリストか — md5/sha1 遮断。

**チームでの安全なパターン**: `hash_password`/`verify_password` を共通モジュール化し、各サービスでの再実装を禁止する。
**事故リスク（低）**: 摩擦点 F-1〜F-3 が診断・テストで担保。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `secrets` モジュール使用（`random` 禁止）・Pydantic 長さ/範囲制限・`ValidationException` 変換・`logging` 使用はすべて準拠。`compare_digest` は「セキュリティは設計の出発点」の実践例。
**初心者でも安全な API 達成度**: `/digest` と `/password` の分離、ホワイトリスト、iterations 上限により、初心者が生ハッシュ保存・弱アルゴリズム・タイミング攻撃・DoS を作り込む余地を構造的に減らせている。
**改善提案**:
- `hash_password` / `verify_password` は `nene2.security`（既に `verify_hmac_signature` がある）に「パスワードハッシュユーティリティ」として昇格する価値がある。
- 将来的に `argon2-cffi` への切り替えパス（`algorithm` フィールドで世代管理）を how-to に明記すると、ハッシュ強度の経年劣化に備えられる。
