# FT201: hashlib モジュール — ハッシュ計算・整合性検証・セキュリティ診断

**日付**: 2026-05-22
**テーマ**: Python `hashlib` モジュールのハッシュ計算・整合性検証・弱アルゴリズム警告の実装と検証
**セキュリティ診断**: **あり**（201 % 3 = 0）
**クラッカーペンテスト**: なし（201 % 4 = 1）

---

## 概要

`hashlib` は Python 標準ライブラリのハッシュ計算モジュール。
SHA-256 / SHA-512 / SHA-3 / BLAKE2 といった強いアルゴリズムから、
MD5 / SHA-1 といったセキュリティ用途には非推奨のアルゴリズムまで対応している。
今回は hashlib の API 検証に加え、タイミング攻撃に安全な比較（`hmac.compare_digest`）の
組み合わせを検証し、「弱いアルゴリズム」を API で明示的に警告するパターンも実装した。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft201-hashlib/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `hash_text(text, algorithm)` | テキストを指定アルゴリズムでハッシュ化。`is_weak` フラグ付き |
| `hash_bytes_data(data, algorithm)` | バイト列をハッシュ化 |
| `verify_integrity(data, expected_hex, algorithm)` | `hmac.compare_digest` でタイミング安全比較 |
| `get_algorithm_info(algorithm)` | ダイジェストサイズ・ブロックサイズ・利用可能性を返す |
| `list_available_algorithms()` | 推奨アルゴリズム一覧（md5/sha1 を除く） |
| `HashResult` | algorithm / hex_digest / digest_size / is_weak を保持する frozen dataclass |
| `FileIntegrityResult` | computed_hex / expected_hex / matches を保持する frozen dataclass |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/hash/text` | テキストをハッシュ化（md5/sha1 は is_weak=true） |
| POST | `/hash/verify` | ハッシュ値を timing-safe に検証 |
| GET | `/hash/algorithms` | 推奨アルゴリズム一覧（md5/sha1 を含まない） |
| POST | `/hash/algorithm-info` | アルゴリズムのメタデータを取得 |

---

## テスト結果

**28 passed**

```
28 passed in 0.06s
```

---

## 摩擦ポイント

### F-1: `hashlib.compare_digest` は存在しない（深刻度: 低）

**事象**: タイミング安全比較のために `hashlib.compare_digest(a, b)` を呼ぼうとしたが
`AttributeError: module 'hashlib' has no attribute 'compare_digest'` が発生。

**原因**: タイミング安全な文字列比較は `hashlib` ではなく `hmac.compare_digest()` に実装されている。
「hmac = HMAC」という先入観からハッシュ比較は hashlib にあると誤解しやすい。

**対応**: `import hmac` を追加し `hmac.compare_digest(computed, expected)` に修正。
CLAUDE.md セキュリティポリシーの「タイミング攻撃: `hmac.compare_digest()` を使用」は既に記載されており、
FT201 でその実所在が確認された。

---

## 観察点

### 観察1: `hashlib.new()` で全アルゴリズムを統一して呼べる

```python
h = hashlib.new("sha256", b"hello")
h.hexdigest()  # → "2cf24dba..."

h = hashlib.new("blake2b", b"hello")
h.hexdigest()  # → 128文字の16進数
```

`hashlib.sha256()` のような直接呼び出しより `hashlib.new(algo_name, data)` の方が
アルゴリズムを変数で扱いやすい。ただし未知のアルゴリズム名を渡すと `ValueError` を送出する。

### 観察2: MD5 / SHA-1 は `hashlib` に存在し有効だが FIPS モードでは無効になることがある

```python
hashlib.new("md5", b"data").hexdigest()  # 通常環境では動く
# FIPS モード (openssl fips=true) の環境では ValueError になる場合がある
```

テスト環境では問題なく動作したが、FIPS 準拠の本番環境での互換性は注意が必要。

### 観察3: `verify_integrity` で `expected_hex.lower()` による大文字小文字正規化

ハッシュ値の比較では大文字小文字を統一する必要がある。
`hmac.compare_digest` は文字単位の等値比較のため、
`"ABCD"` と `"abcd"` は異なる文字列として扱われる。
`expected_hex.lower()` で正規化することで大文字小文字不一致による誤否定を防いだ。

---

## nene2-python フレームワークとの統合

- `hash_text()` の `algorithm` パラメータは Pydantic の `Literal` 型で厳密に制限。
  `AllowedAlgorithm = Literal["sha256", "sha512", "sha3_256", "sha3_512", "blake2b", "blake2s", "md5", "sha1"]`
  これにより任意文字列のアルゴリズム名インジェクションを Pydantic 層でブロックできる。
- `is_weak: bool` フィールドで弱アルゴリズム使用を API レスポンスで明示。クライアント側でのリスク警告が可能。
- `verify_integrity` は `hmac.compare_digest` を使うことでタイミングサイドチャネルを排除。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

ファイルの整合性チェック機能を API に追加しようとしている。

**ドキュメント理解**: `hashlib.sha256(data).hexdigest()` は直感的。
`hashlib.new()` による動的アルゴリズム選択は少しわかりにくいが、
`hashlib.algorithms_guaranteed` で利用可能なアルゴリズムを確認できる。  
**事故リスク**: 中。MD5/SHA-1 を「速いから」という理由で選ぶリスクがある。
`is_weak=true` フラグで警告を返す設計が防御になる。  
**規約の使いやすさ**: `hash_text()` を一度理解すれば機械的に使える。タイミング攻撃の概念は説明が必要。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

既存システムに「チェックサム検証機能」を追加する作業を担当している。

**コピペ可能性**: `hash_text()` / `verify_integrity()` はコピーして即使える。
`hmac.compare_digest` の代わりに `==` で比較するコードをコピーすると timing leak になるが、
FT201 のサンプルに正しいパターンが明示されているので防ぎやすい。  
**拡張時の罠**: MD5/SHA-1 のアルゴリズム名を直打ちして使う場合に `is_weak` 警告を見落とすリスク。  
**セキュリティ的な事故リスク**: 中。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

ファイルアップロード後の整合性チェック API を実装している。

**エラーレスポンスの質**: 整合性検証は 200 + `matches: false` で返す設計。
「どのアルゴリズムで計算したか」も `algorithm` フィールドで返るため、
クライアントがデバッグしやすい。  
**Python 固有概念の学習コスト**: `hmac.compare_digest` が `hashlib` でなく `hmac` モジュールにある点は
TypeScript/Node.js の `crypto.timingSafeEqual` に近い概念として説明できる。  
**事故リスク**: 低。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

セキュリティ重視のサービスで hash 関連機能を実装する経験がある。

**他フレームワークとの差異**: Django の `make_password` / `check_password` はパスワードハッシュ専用で
bcrypt/argon2 を使う。今回の FT は汎用ハッシュ（データ整合性・チェックサム）を対象としており用途が異なる。
パスワードハッシュには `passlib` や `argon2-cffi` を別途使うべきという認識が必要。  
**nene2-python の薄さへの評価**: `AllowedAlgorithm = Literal[...]` によるアルゴリズム制限は好評価。  
**本番投入可能性**: ファイル整合性・チェックサム検証用途には問題なし。パスワードハッシュには使わない。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

セキュリティポリシー準拠のコードレビューを担当する。

**コードレビューチェックポイント**:
- [ ] ハッシュ比較が `==` でなく `hmac.compare_digest` を使っているか
- [ ] MD5/SHA-1 の使用に `is_weak=true` フラグが付いているか（パスワードハッシュへの流用防止）
- [ ] `hashlib.new()` に渡すアルゴリズム名が Pydantic `Literal` で制限されているか

**チームでの安全な共有パターン**: `verify_integrity()` を整合性比較の唯一の入口とし、
生の `==` 比較を禁止するガイドラインが有効。  
**ツール追加の必要性**: bandit（ruff S）の `S324` ルールが MD5/SHA-1 使用を警告するが、
`is_weak` フラグで意図的な使用を許容している本実装では許容範囲。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高。CLAUDE.md セキュリティポリシー「タイミング攻撃: `hmac.compare_digest()` を使用」が実装された。  
**「初心者でも安全な API」達成度**: 高。`is_weak` フラグで弱アルゴリズムのリスクを明示。
`AllowedAlgorithm = Literal[...]` でアルゴリズムインジェクションを防いでいる。  
**設計上の負債・ドキュメント不足**: `compare_digest` が `hmac` モジュールにある点は CLAUDE.md 既記載。FT201 で確認済み。  
**Follow-up Issue 候補**: なし

---

## セキュリティ診断

### 1. OWASP API Security Top 10 (2023)

#### API1: オブジェクトレベルの認可不備 (BOLA / IDOR)
認証なしのステートレス API。オブジェクト所有権の概念がないためスコープ外。  
**結果**: 該当なし ✅

#### API3: オブジェクトプロパティレベルの認可不備 (Mass Assignment)
- `{"text": "hello", "is_weak": False, "admin": True}` を送信 → `is_weak` は実際のアルゴリズムに基づいて計算され、送信値は無視された。  
**結果**: ✅ Pydantic が定義外フィールドを無視

#### API4: 無制限リソース消費
- `text: "A" * 65536` → 200（上限ちょうど）
- `text: "A" * 65537` → 422（Pydantic max_length 超過）  
**結果**: ✅

#### API6: SSRF
hashlib は外部リクエストを行わないためスコープ外。  
**結果**: 該当なし ✅

#### API7: セキュリティ設定ミス
- `GET /hash/algorithms` は md5/sha1 を返さない（弱アルゴリズムを推奨リストから除外）
- `POST /hash/text` で md5/sha1 を使うと `is_weak: true` を明示して返す  
**結果**: ✅

### 2. インジェクション攻撃

#### コマンドインジェクション（アルゴリズム名経由）
```
{"text": "hello", "algorithm": "__import__(\"os\").system(\"id\")"}  → 422
{"text": "hello", "algorithm": "sha256; DROP TABLE--"}              → 422
{"text": "hello", "algorithm": "../../etc/passwd"}                  → 422
```
`AllowedAlgorithm = Literal[...]` により Pydantic 層で完全に遮断される。  
**結果**: ✅ インジェクション不可

#### パストラバーサル
hashlib はファイルシステムに触れないためスコープ外。  
**結果**: 該当なし ✅

### 3. 認証・認可

- タイミング攻撃: `verify_integrity` は `hmac.compare_digest` で定時間比較を実装
- `==` 比較を使っていないことを確認  
**結果**: ✅

### 4. 入力バリデーション

- `text` フィールド: `max_length=65536` で上限制限
- `expected_hex` フィールド: `max_length=128` で上限制限（SHA-512 の 128 文字が最長）
- `algorithm` フィールド: `Literal[...]` で許可リスト制限
- Unicode 正規化不要（ハッシュは byte-level で動作）  
**結果**: ✅

### 5. 情報漏洩

- エラーレスポンスにスタックトレース含まず（`ErrorHandlerMiddleware` が Problem Details 形式で返す）
- `algorithm-info` に未知アルゴリズムを渡すと `is_available: false` を返すが内部情報は漏洩しない  
**結果**: ✅

### 6. Python / FastAPI 固有の攻撃ベクター

#### 型強制攻撃
- `{"algorithm": 123}` → 422（`AllowedAlgorithm = Literal` は整数を拒否）  
**結果**: ✅

#### ReDoS
`hashlib` に正規表現処理はない。入力文字列はそのまま `encode("utf-8")` でバイト変換。  
**結果**: 該当なし ✅

### 7. 依存関係の脆弱性スキャン

```
uv run pip-audit → No known vulnerabilities found
```

**スキャン結果**: CVE: 0件  
**対応方針**: 対応不要

### 診断サマリー

| カテゴリ | 結果 | 最重要発見 |
|---|---|---|
| OWASP API Security Top 10 | ✅ 全通過 | - |
| インジェクション攻撃 | ✅ | Literal 型でアルゴリズム名インジェクション完全遮断 |
| 認証・認可 | ✅ | hmac.compare_digest で timing-safe 比較 |
| 入力バリデーション | ✅ | max_length + Literal で全境界保護 |
| 情報漏洩 | ✅ | - |
| ReDoS | 該当なし | - |
| 型強制攻撃 | ✅ | - |
| 依存関係 CVE | ✅ | 0件 |

**総合評価**: 合格  
**発見した脆弱性**: 0件  
**新規セキュリティ Issue**: なし

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| — | なし | — |

---

## まとめ

`hashlib` モジュールの FT は、ハッシュ計算そのものより周辺のセキュリティ設計が学びの中心となった。
「タイミング安全比較は `hmac.compare_digest`（`hashlib` でなく）」という発見（F-1）が主な摩擦点で、
CLAUDE.md のセキュリティポリシーにすでに記載されていた内容が実装で確認された形となった。

セキュリティ診断では全カテゴリを通過。`AllowedAlgorithm = Literal[...]` によるアルゴリズム名の
許可リスト制限が最も効果的な防御層であることを確認した。

次の FT202 は `202 % 3 = 1` → 診断なし、`202 % 4 = 2` → ペンテストなし。
