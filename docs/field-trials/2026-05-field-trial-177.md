# FT177: hashlib モジュール

**日付**: 2026-05-21
**テーマ**: 安全なハッシュ・パスワード保護・ファイル整合性検証（PBKDF2 / scrypt / Blake2）
**セキュリティ診断**: **あり**（177 % 3 = 0）

---

## 概要

Python 標準の `hashlib` モジュールを nene2-python 上で検証する。
単なる SHA-256 だけでなく、パスワード保護 (PBKDF2・scrypt)、MAC 生成 (Blake2 キー付き)、
ファイル整合性検証（チャンク読み込み）まで網羅し、暗号的に安全な実装パターンを確立する。
FT177 は 3 の倍数のためセキュリティ診断も実施する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft177-hashlib/`

### 主要機能

| 関数/定数 | 概要 |
|---|---|
| `SECURE_ALGORITHMS` | 許可リスト (`sha256`, `sha512`, `sha3_256`, `sha3_512`, `blake2b`, `blake2s`) |
| `INSECURE_ALGORITHMS` | 拒否リスト (`md5`, `sha1`, `sha224`) |
| `hash_text(text, algorithm)` | テキストをハッシュ化（非推奨アルゴリズムは `None` 返却） |
| `hash_bytes(data, algorithm)` | バイト列をハッシュ化 |
| `hash_streaming(chunks, algorithm)` | イテレータからチャンク単位でハッシュ化 |
| `available_algorithms()` | 安全/非推奨/その他に分類した一覧 |
| `generate_salt()` | `secrets.token_hex(32)` — 256-bit 暗号論的乱数 salt |
| `hash_password(password, salt, iterations)` | PBKDF2-HMAC-SHA256（最低 200,000 イテレーション） |
| `verify_password(password, stored_hash, salt)` | `hmac.compare_digest` によるタイミングセーフ検証 |
| `scrypt_hash(password, salt)` | scrypt (N=16384, r=8, p=1) — メモリハード KDF |
| `blake2_keyed_hash(data, key)` | Blake2b キー付きハッシュで MAC 生成 |
| `verify_blake2_mac(data, key, expected_mac)` | Blake2b MAC のタイミングセーフ検証 |
| `hash_file_content(content, algorithm)` | 64 KB チャンク処理でファイルをハッシュ化 |
| `verify_file_integrity(content, expected_hash)` | ファイル整合性のタイミングセーフ検証 |
| `generate_token(length)` | SHA-256 ベースのセキュアトークン生成 |
| `derive_key_for_purpose(master_key, purpose)` | 用途別鍵導出（PBKDF2 で purpose を salt に使用） |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/algorithms` | 安全/非推奨アルゴリズム一覧 |
| POST | `/hash` | テキストをハッシュ化 |
| POST | `/password/hash` | PBKDF2 パスワードハッシュ（salt 自動生成可） |
| POST | `/password/verify` | パスワード検証（タイミングセーフ） |
| POST | `/password/scrypt` | scrypt パスワードハッシュ |
| POST | `/mac/blake2` | Blake2b MAC 生成 |
| POST | `/mac/verify` | Blake2b MAC 検証（タイミングセーフ） |
| POST | `/file/verify` | ファイル整合性検証 |

---

## テスト結果

**62 passed**

```
62 passed in 2.04s
```

mypy: Success（3 ファイル、エラーゼロ）  
ruff check: All checks passed  
ruff format: 3 files reformatted → 再チェックで already formatted

---

## 摩擦ポイント

### F-1: `@app.post` デコレータが `create_app()` 返却インスタンスに適用されない（深刻度: 中）

**事象**: app.py でモジュールレベルに `app = create_app()` を作成し `@app.post(...)` でルートを定義した。
`TestClient(create_app())` が新しい FastAPI インスタンスを返すためルートが空になり、全エンドポイントで 404 が返る。

**原因**: デコレータは定義時の `app` オブジェクトにルートを登録する。
`create_app()` は呼ぶたびに新規インスタンスを返すので、モジュールレベルの `app` と別インスタンスになる。

**対応**: `APIRouter` を使用し、`create_app()` の中で `application.include_router(router)` する。
FT170 以降で繰り返し発生しているため、init-ft.sh のテンプレートまたは CLAUDE.md に「FastAPI アプリファクトリは `APIRouter` パターンを使う」旨を追記する。

---

## 観察点

### 観察1: アルゴリズム許可リスト — 拒否側ではなく許可側で制御

```python
SECURE_ALGORITHMS = frozenset({"sha256", "sha512", "sha3_256", "sha3_512", "blake2b", "blake2s"})

def hash_text(text: str, algorithm: str = "sha256") -> str | None:
    if algorithm not in SECURE_ALGORITHMS:
        return None
    ...
```

`if algorithm in INSECURE_ALGORITHMS: return None` ではなく許可リストで制御することで、
未知の新アルゴリズムが追加されても自動的に拒否される。セキュリティ設計の基本原則。

### 観察2: PBKDF2 最低イテレーション数の強制

```python
MIN_PBKDF2_ITERATIONS = 200_000  # NIST SP 800-132 推奨最低値

def hash_password(password: str, salt: str, iterations: int = MIN_PBKDF2_ITERATIONS) -> str:
    if iterations < MIN_PBKDF2_ITERATIONS:
        iterations = MIN_PBKDF2_ITERATIONS
    ...
```

API 側で `ge=200_000` の Pydantic バリデーションも設けているが、`demos.py` 側でも下限を強制する二重防御。
ドメイン層がセキュリティ制約を持つことでHTTP 以外から呼ばれても安全を保てる。

### 観察3: `hmac.compare_digest` の徹底

パスワード検証・MAC 検証・ファイル整合性検証の全 3 か所で `==` 比較ではなく
`hmac.compare_digest` を使用。タイミングサイドチャネル攻撃（timing attack）への対策。

### 観察4: scrypt vs PBKDF2 の使い分け

scrypt はメモリハード（N=16384 では約 16 MB のメモリを消費）のため、
GPU/ASIC による総当たり攻撃に対して PBKDF2 より強い。
ただしサーバーリソースも多く消費するため、高負荷環境では PBKDF2 が現実的。
テストで両者が異なる出力を生成することを確認済み。

---

## nene2-python フレームワークとの統合

- `APIRouter` + `create_app()` パターンは nene2-python の標準的な設計に沿う（F-1 の解決策）
- `hash_password` / `verify_password` は UseCase 層に組み込める純粋関数として設計
- Pydantic の `max_length` 制限で DoS 防止（`password` は 1,000文字、`text` は 10,000文字）
- HTTP 境界での入力バリデーション（`ge=200_000` など）とドメイン層の二重防御がポリシー準拠

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

認証機能を初めて実装しようとしており、「パスワードをハッシュ化する」という要件がある。

**ドキュメント理解**: `hash_password()` 関数の存在を見つけられれば使えるが、
「なぜ `iterations=200_000` が必要か」「salt とは何か」の説明がコード内コメントにないため、
コピペして使うとイテレーション数を削って「速くした」事故が起きやすい。  
**事故リスク**: 中。`hash_password("secret", generate_salt(), iterations=1000)` は動作するが危険。
ドキュメントなしでは最低イテレーション数の意味が分からない。  
**規約の使いやすさ**: `generate_salt()` → `hash_password()` → `verify_password()` の3点セットが分かりやすい。
型注釈があるので補完で辿れる。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

既存の `hashlib.md5(password.encode()).hexdigest()` を使ったコードを見て「これでいいか」と思っている。

**コピペ可能性**: `hash_text("password", "md5")` が `None` を返すことで明示的に失敗する設計は良い。
ただし `None` チェックを怠ると `None.hex()` で AttributeError になり、デバッグが難しい場面もある。  
**拡張時の罠**: `SECURE_ALGORITHMS` に直接 `"md5"` を追加してしまうと全防御が崩れる。
定数を immutable (`frozenset`) にしているのは良い。  
**セキュリティ的な事故リスク**: 中。パスワードに `hash_text()` を使うと salt なし → 同じパスワードが同じハッシュになるという致命的なミスが可能。`hash_password()` を使わせるガイドが必要。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

パスワード登録・ログイン API を TypeScript クライアントから叩く立場。

**エラーレスポンスの質**: `algorithm: "md5"` を送ると `400 Bad Request` が返り、
`"Insecure or unsupported algorithm: md5"` というメッセージが返る。クライアント実装には十分。  
**Python 固有概念の学習コスト**: `bytes.fromhex(salt)` や `derived.hex()` はバイト⇔文字列変換の理解が必要。
TypeScript の `Buffer.from(hex, 'hex')` に相当するが、知らないと戸惑う。  
**事故リスク**: 低。HTTP 境界での Pydantic バリデーションが充実しており、不正入力は400で弾かれる。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `make_password()` / `check_password()` を使い慣れており、代替実装を評価する。

**他フレームワークとの差異**: Django は `pbkdf2_sha256$N$salt$hash` 形式で保存するが、
このFTでは hash と salt を別フィールドで管理するシンプルな形式。
移行時にはシリアライズ形式を揃える必要がある。  
**nene2-python の薄さへの評価**: `hash_password` / `verify_password` が純粋関数なのは好評。
UseCase に組み込んでもHTTPの知識が不要なのは Django の `auth` モジュール依存より明快。  
**本番投入可能性**: scrypt の `N=2**14` は WSL2 環境で問題ないが本番では `N=2**16` 以上を推奨。
テストが遅くなるのでテスト専用の低 N 設定が必要になる場面がある。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

チームでこのコードをレビューする際のリスク評価。

**コードレビューチェックポイント**:
- [x] `hash_text()` をパスワードハッシュに使っていないか（salt なし → レインボーテーブル攻撃可能）
- [x] `iterations` パラメータが 200,000 未満にオーバーライドされていないか
- [x] `hmac.compare_digest` ではなく `==` でハッシュ比較していないか（timing attack）
- [x] salt が `generate_salt()` 以外（固定文字列など）で生成されていないか

**チームでの安全な共有パターン**: `hash_password` / `verify_password` の組み合わせで使うことを
ADR またはドキュメントで明文化すると良い。`hash_text` はファイル整合性など非パスワード用途専用と明示。  
**ツール追加の必要性**: `ruff S303`（`hashlib.md5`/`sha1` を使用している場合の警告）が有効。
ただし `SECURE_ALGORITHMS` チェックがあるため検出は二重になる。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

CLAUDE.md との整合性確認。

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 中  
— `hash_text()` がパスワードハッシュに誤用される余地がある点でやや低い。
関数名を `hash_content()` に変え、パスワード用途は明示的に `hash_password()` のみにする設計も検討できる。  
**設計上の負債・ドキュメント不足**:
- F-1 (APIRouter パターン) は CLAUDE.md または init-ft.sh テンプレートに追記が必要
- scrypt の N パラメータが環境依存なのでテスト時と本番時の設定分離ガイドが欲しい  
**Follow-up Issue 候補**: F-1 の APIRouter パターン文書化 → Issue #501

---

## セキュリティ診断

> **診断方針**: 今回は hashlib 自体がセキュリティモジュールのため、
> 「hashlib の誤用パターン」が主な検査対象となる。

### 1. OWASP API Security Top 10 (2023)

#### API1: オブジェクトレベルの認可不備 (BOLA / IDOR)
- 認証・認可が絡むエンドポイントなし（ハッシュ計算と検証のみ）
- **結果**: ✅ 該当なし

#### API2: 認証の破損 (Broken Authentication)
- 認証ミドルウェアなし（FT なので最小構成）
- パスワード検証ロジック自体は `hmac.compare_digest` でタイミングセーフ
- **結果**: ✅ 設計上の問題なし

#### API3: オブジェクトプロパティレベルの認可不備 (Mass Assignment)
- Pydantic の `BaseModel` はデフォルトで定義外フィールドを無視
- `{"password": "x", "is_admin": true}` を POST → `is_admin` は無視される
- **結果**: ✅ 問題なし

#### API4: 無制限リソース消費 (Unrestricted Resource Consumption)
- `password`: `max_length=1_000` / `text`: `max_length=10_000` / `content_hex`: `max_length=20_971_520`
- `demos.py` 側でも `MAX_INPUT_BYTES = 10 * 1024 * 1024` チェック
- scrypt は計算コストが高い（`N=16384` で約 50ms）— Pydantic 入力バリデーションでペイロードサイズは制限済み
- **結果**: ✅ DoS ベクター対策済み

#### API5〜API10
- SSRF: 外部 URL を受け取るエンドポイントなし ✅
- セキュリティヘッダー: FT 最小構成のため nene2 ミドルウェアなし（本番投入時に追加必須）
- デバッグエンドポイント: `/docs` は残存（FT 環境は許容）
- **結果**: ✅ FT スコープ内では問題なし

---

### 2. インジェクション攻撃

#### SQL インジェクション
- DB アクセスなし
- **結果**: ✅ 該当なし

#### コマンドインジェクション
- `subprocess` / `os.system` 使用なし（ruff S602/S605 確認済み）
- **結果**: ✅

#### パストラバーサル
- ファイルパス操作なし（`content` は bytes として受け取る）
- **結果**: ✅ 該当なし

#### SSTI / HTTP ヘッダーインジェクション
- テンプレートエンジン使用なし / レスポンスヘッダーへのユーザー入力反映なし
- **結果**: ✅

---

### 3. 認証・認可

- **パスワードハッシュ**: PBKDF2-HMAC-SHA256 (200,000 iterations) / scrypt (N=16384) 実装済み ✅
- **salt 生成**: `secrets.token_hex(32)` — 256-bit 暗号論的乱数 ✅
- **MD5・SHA-1 拒否**: `SECURE_ALGORITHMS` 許可リストで完全拒否 ✅
- **タイミング攻撃**: `hmac.compare_digest` を全検証箇所で使用 ✅
- **JWT**: 使用なし（PYSEC-2025-183 の影響なし）✅

---

### 4. 入力バリデーション

実際の攻撃ペイロードを TestClient で送信:

```python
# 巨大入力
POST /hash {"text": "A" * 100_001}
# → 422 Unprocessable Entity (max_length=10_000)

# 最低イテレーション未満
POST /password/hash {"password": "x", "iterations": 1000}
# → 422 (ge=200_000)

# 無効な hex
POST /file/verify {"content_hex": "ZZZZ", "expected_hash": "..."}
# → 400 "Invalid hex content"

# 非 ASCII algorithm
POST /hash {"text": "hello", "algorithm": "SHA-256"}
# → 400 "Insecure or unsupported algorithm: SHA-256"
```

- **結果**: ✅ 全ペイロードで適切なエラーが返る

---

### 5. 情報漏洩

- hashlib の内部エラーは `except ValueError` でキャッチして `400` に変換
- スタックトレースは FastAPI のデフォルト動作で非公開（`APP_DEBUG` 未設定）
- `pip-audit` 結果: `PYSEC-2025-183` (PyJWT 2.12.1 / mcp 経由の推移的依存)
  — 直接使用なし、Fix バージョン未提供のため**許容**（FT174 以降と同じ判断）
- **結果**: ⚠️ PYSEC-2025-183 は継続監視（修正版リリース待ち）

---

### 6. Python / FastAPI 固有の攻撃ベクター

#### ReDoS
- 正規表現使用なし
- **結果**: ✅ 該当なし

#### pickle / yaml インジェクション
- `pickle` / `yaml.load` 使用なし
- **結果**: ✅

#### 非同期レースコンディション
- グローバルな mutable 状態なし（全関数が純粋関数）
- **結果**: ✅

#### 型強制攻撃 (Pydantic)

```python
POST /password/hash {"password": "x", "iterations": "2e5"}
# → 200 OK (iterations = 200000 として型変換)

POST /password/hash {"password": "x", "iterations": 1.5}
# → 422 (int フィールドに float は不正)
```

`"2e5"` が 200000 に変換されるのは Pydantic v2 の仕様（許容範囲内、200,000 >= `ge=200_000`）。  
**結果**: ✅ セキュリティ上の問題なし（`ge` 制約が通過するため）

#### hashlib 特有: アルゴリズム名インジェクション

```python
POST /hash {"text": "hello", "algorithm": "sha256;DROP TABLE--"}
# → 400 "Insecure or unsupported algorithm: sha256;DROP TABLE--"
# SECURE_ALGORITHMS の frozenset チェックで即拒否
```

- **結果**: ✅ 許可リスト方式で任意文字列を `hashlib.new()` に渡さない

---

### 7. 依存関係の脆弱性スキャン

```
Found 1 known vulnerability in 1 package
Name  Version ID             Fix Versions
----- ------- -------------- ------------
pyjwt 2.12.1  PYSEC-2025-183
```

- **スキャン結果**: CRITICAL: 0件 / HIGH: 0件 / MEDIUM: 0件 / LOW: 1件（PyJWT 経由）
- **対応方針**: 直接使用なし・mcp の推移的依存・Fix バージョン未提供のため許容

---

### 診断サマリー

| カテゴリ | 結果 | 最重要発見 |
|---|---|---|
| OWASP API Security Top 10 | ✅ 全通過 | - |
| SQL インジェクション | ✅ 該当なし | - |
| コマンドインジェクション | ✅ | - |
| パストラバーサル | ✅ 該当なし | - |
| SSTI | ✅ 該当なし | - |
| 認証・認可 | ✅ | PBKDF2+scrypt+Blake2 全対応 |
| 入力バリデーション | ✅ | 全境界で max_length/ge/le 設定済み |
| 情報漏洩 | ⚠️ | PYSEC-2025-183（継続監視） |
| ReDoS | ✅ 該当なし | - |
| pickle / yaml | ✅ | - |
| 非同期レースコンディション | ✅ | - |
| 型強制攻撃 | ✅ | `"2e5"` 変換は仕様範囲内 |
| アルゴリズム名インジェクション | ✅ | 許可リスト方式で完全防御 |
| 依存関係 CVE | ⚠️ 1件 | PYSEC-2025-183（PyJWT/mcp 経由） |

**総合評価**: 条件付き合格（PYSEC-2025-183 を継続監視）  
**発見した脆弱性**: 0件（CRITICAL: 0 / HIGH: 0 / MEDIUM: 0 / LOW: 0 ※CVE は推移的依存）  
**新規セキュリティ Issue**: #501（APIRouter パターン文書化）

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 中 | F-1: FastAPI アプリファクトリで APIRouter パターンを CLAUDE.md または init-ft.sh に記載 | docs |
| 低 | scrypt の N パラメータをテスト/本番で分ける設定ガイドを追加 | docs |

---

## まとめ

FT177 では `hashlib` を中心に、PBKDF2・scrypt・Blake2 キー付きハッシュという3種のセキュリティプリミティブを実装した。
62 テストが全通過し、mypy/ruff も問題なし。

セキュリティ診断では「hashlib そのものがセキュリティモジュール」という特性から
インジェクション系のリスクはほぼ皆無だったが、**アルゴリズム名インジェクション**に対する
許可リスト方式の有効性を実証でき、今後の設計パターンとして参照できる。

主要摩擦点は F-1 の `@app.post` と `create_app()` の分離問題（毎 FT で発生）で、
`APIRouter` パターンへの移行を次 FT 以降の標準とする。

v1.8.48 としてリリース。
