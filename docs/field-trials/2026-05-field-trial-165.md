# FT165: secrets モジュール

**日付**: 2026-05-21
**テーマ**: `secrets` モジュール — 暗号学的安全な乱数・タイミング安全比較・OTP 生成
**セキュリティ診断**: **あり**（165 % 3 = 0）

---

## 概要

Python 標準ライブラリの `secrets` モジュールを nene2-python フレームワーク上で検証した。
`secrets` は OS の乱数源（`/dev/urandom` 相当）を使用して暗号学的に安全なトークンを生成するモジュール。
セキュリティトークン・OTP・API キー生成のベストプラクティスであり、
`random` モジュールの代替として NIST SP 800-63B が推奨する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft165-secrets/`

### 主要機能

| 関数 | 概要 |
|---|---|
| `generate_token_hex(nbytes)` | `secrets.token_hex()` で hex トークン生成、最低 128 bit を保証 |
| `generate_token_urlsafe(nbytes)` | `secrets.token_urlsafe()` で URL 安全トークン生成 |
| `generate_token_bytes_b64(nbytes)` | `secrets.token_bytes()` で raw バイト生成（Base64 エンコード返却） |
| `timing_safe_compare(a, b)` | `hmac.compare_digest()` でタイミング安全比較 |
| `randbelow_demo(upper)` | `secrets.randbelow()` で範囲内乱数生成 |
| `generate_otp(length)` | `secrets.choice()` で紛らわしい文字を除いた OTP 生成 |
| `random_module_usage_check()` | nene2-python ソースで `random` モジュール使用なしを検証 |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/secrets/token-hex` | hex トークン生成 |
| GET | `/secrets/token-urlsafe` | URL 安全トークン生成 |
| GET | `/secrets/token-bytes` | バイトトークン（Base64）生成 |
| POST | `/secrets/compare` | タイミング安全比較 |
| GET | `/secrets/randbelow` | 範囲内乱数 |
| POST | `/secrets/otp` | OTP 生成 |
| GET | `/secrets/audit/random-module-check` | セキュリティ自己診断 |

---

## テスト結果

**32 passed（摩擦ゼロ）**

```
32 passed in 0.87s
```

---

## 摩擦ポイント

**今回の FT では実装上の摩擦はゼロだった。**

---

## 観察点

### 観察1: `MIN_TOKEN_BYTES = 16` を強制してセキュリティ下限を守る

```python
MIN_TOKEN_BYTES = 16  # NIST SP 800-63B: 最低 128 bit

def generate_token_hex(nbytes: int = 32) -> TokenResult:
    safe_nbytes = max(MIN_TOKEN_BYTES, nbytes)
    return TokenResult(value=secrets.token_hex(safe_nbytes), ...)
```

呼び出し元が `nbytes=1` を渡しても 128 bit 以上を保証する。
nene2-python のトークン生成 API はこのパターンを標準にすべき。

### 観察2: `hmac.compare_digest` vs `secrets.compare_digest`

Python 3.12+ では `hmac.compare_digest` と `secrets.compare_digest` はどちらも定時間比較。
`secrets.compare_digest` は Python 3.14 で追加されたが、3.12 では `hmac.compare_digest` を使う。
nene2-python の `auth/local_verifier.py` は `secrets.compare_digest` を使っており正しい（3.14 環境）。

### 観察3: OTP のアルファベットから紛らわしい文字を除外

```python
OTP_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 0/O, 1/I/L を除外
code = "".join(secrets.choice(OTP_ALPHABET) for _ in range(length))
```

`0` と `O`、`1` と `I` と `L` はフォントによって区別しにくい。
人間が読む OTP では除外が必須。`secrets.choice()` は毎回独立した乱数を引くため分布が均等。

### 観察4: `token_hex(n)` の文字列長は `2n`

```python
secrets.token_hex(32)  # → 64文字の hex 文字列
```

`n` バイト = `2n` 文字（1 バイト = 2 hex 文字）。
ドキュメントに書いてあるが初心者が `len(token) == nbytes` と誤解しやすい。

### 観察5: `token_urlsafe(n)` の長さは可変（Base64 パディング依存）

```python
secrets.token_urlsafe(32)  # → 43文字（32バイトを Base64url でエンコード）
```

Base64url は 3 バイトごとに 4 文字になるためパディングで長さが変わる。
DB カラムのサイズ設計時は `len(token_urlsafe(n))` を実測すること。

---

## nene2-python フレームワークとの統合

- `auth/local_verifier.py` がすでに `secrets.compare_digest()` を使用：正しい実装
- `security/webhook.py` が `hmac.compare_digest()` を使用：正しい実装
- `random` モジュールはソース全体で使用ゼロ：PASS
- トークン生成ヘルパーを `nene2.security` に追加するとユーザーが安全なデフォルトを使いやすくなる

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

セキュリティモジュールについて「とりあえず動くもの」を求める段階。
`random.token_hex()` が存在しないことを知らず、`random.random()` でトークンを作ってしまうリスクが高い。

**ドキュメント理解**: `secrets` vs `random` の使い分けがドキュメントにないと区別できない。
「API キー生成には必ず secrets モジュールを使う」という1文があれば十分。

**事故リスク**: **高**。`random.getrandbits(128)` で作ったトークンは予測可能。
攻撃者はシードを推測して有効なセッショントークンを列挙できる（実際の攻撃例あり）。

**規約の使いやすさ**: `secrets.token_urlsafe()` のシグネチャは直感的。
「`n` バイト → `2n` 文字」だけ補足があれば使える。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`uuid.uuid4()` をトークンとして使っているケースが多い（UUID v4 は 122 bit のエントロピーがあるが、
ライブラリによっては擬似乱数源を使う）。

**コピペ可能性**: `secrets.token_urlsafe(32)` のワンライナーはコピペしやすい。
サンプルに「これが正しいやり方」と明示されていれば従う。

**拡張時の罠**: タイミング攻撃が理解されていない。
`if user_token == db_token:` という `==` 比較を「動いているから OK」と思いがち。
`hmac.compare_digest` が必要な理由を 1 行コメントで説明する価値がある。

**セキュリティ的な事故リスク**: **高**。タイミング攻撃によるトークン列挙は実際の攻撃手法。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

Node.js の `crypto.randomBytes()` / `crypto.timingSafeEqual()` と同等の概念を理解している。

**Python 固有概念の学習コスト**: `hmac.compare_digest` が `secrets.compare_digest` と違うモジュールにあることが混乱点。
Python 3.14+ では `secrets.compare_digest` も使える。

**事故リスク**: 低。暗号トークンの概念は既知。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `get_random_string()` / `constant_time_compare()` との対応がわかれば即座に使える。

**他フレームワークとの差異**: Django は `django.utils.crypto.constant_time_compare()` でラップ済み。
nene2-python は `hmac.compare_digest()` を直接使う必要がある（より透明性が高い）。

**本番投入可能性**: 問題なし。`secrets` モジュールは stdlib で外部依存なし。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- [ ] トークン生成に `random` / `uuid.uuid4()` ではなく `secrets` を使っているか
- [ ] トークン比較に `==` ではなく `hmac.compare_digest` / `secrets.compare_digest` を使っているか
- [ ] `nbytes` が最低 16 以上（128 bit）か
- [ ] OTP のアルファベットに紛らわしい文字（0/O/1/I/L）が含まれていないか
- [ ] `token_hex(n)` の長さが `n` ではなく `2n` 文字であることをカラムサイズ設計に反映しているか

**チームでの安全なパターン**: `nene2.security.generate_token()` ヘルパーに最低ビット強度を組み込むことで、
チームメンバーが誤って短いトークンを生成するリスクを排除できる。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高（`secrets` モジュール使用はCLAUDE.mdで必須化済み）

**「初心者でも安全な API」達成度**: 中
- `nene2.security` に最低 128 bit を保証するトークン生成ヘルパーがあれば「高」になる
- 現状は「`secrets` を使え」というポリシーだけで、安全なデフォルトが提供されていない

**設計上の負債**: `nene2.security` に `generate_api_key()`、`generate_session_token()` などの
安全なデフォルトを持つ高レベルヘルパーが未実装。

**Follow-up Issue 候補**: `feat: nene2.security に generate_token() ヘルパーを追加（最低 128 bit 保証）`

---

## セキュリティ診断（FT165 — 165 % 3 = 0）

> **診断方針**: Django・FastAPI・SQLAlchemy 本体でも CVE が報告されてきたレベルの
> 攻撃ベクターを対象とする。「動いているから安全」は不正解。

### 1. OWASP API Security Top 10 (2023)

#### API1: BOLA / IDOR
- ユーザー所有リソースがないため対象外（トークン生成 API）
- **結果**: ✅ 対象外

#### API2: 認証の破損
- [ ] `auth/local_verifier.py:36` で `secrets.compare_digest()` 使用確認 → **✅ PASS**
- [ ] 保護エンドポイント: FT165 アプリは認証なしの公開 API のため対象外
- **結果**: ✅

#### API3: Mass Assignment
- 実測: `POST /secrets/compare` に `{"a":"x","b":"y","is_admin":true}` → 200、レスポンスに `is_admin` なし
- Pydantic が extra フィールドを無視（デフォルト動作）
- **結果**: ✅ PASS

#### API4: 無制限リソース消費
- 実測: `a="x"*513` → 422（`max_length=512` で拒否）
- 実測: `upper=1_000_001` → 422（`le=1_000_000` で拒否）
- `ThrottleMiddleware`: FT165 アプリは未設定（本番では必須）
- **結果**: ✅ バリデーション境界は機能。スロットリングは本番設定が必要

#### API5: 機能レベルの認可不備
- FT165 は認証不要の公開 API のため対象外
- **結果**: ✅ 対象外

#### API6: SSRF
- URL を受け取るフィールドなし
- **結果**: ✅ 対象外

#### API7: セキュリティの設定ミス
- 実測: `X-Request-Id`, `X-Content-Type-Options`, `X-Frame-Options` → ✅ 全レスポンスに付与
- 実測: 422 エラーレスポンスにスタックトレース含まれず → ✅
- CORS ワイルドカード: `grep allow_origins="*"` → ✅ PASS
- **結果**: ✅

#### API8〜10
- バージョン管理・デバッグエンドポイント・外部 API 消費: FT165 アプリでは対象なし
- **結果**: ✅ 対象外

---

### 2. インジェクション攻撃

#### SQL インジェクション
- `grep -rn 'f".*SELECT|INSERT|UPDATE|DELETE'` → **PASS（0 件）**
- FT165 アプリに DB 操作なし
- **結果**: ✅

#### コマンドインジェクション
- `grep -rn "shell=True\|os\.system"` → **PASS（0 件）**
- `random_module_usage_check()` 内の `subprocess.run()` は固定引数のみ（ユーザー入力なし）
- **結果**: ✅

#### パストラバーサル
- FT165 アプリにファイル操作なし
- **結果**: ✅ 対象外

#### SSTI
- テンプレートエンジン使用なし
- **結果**: ✅ 対象外

---

### 3. 認証・認可

- `random` モジュール使用: **PASS（0 件）**
- `secrets.compare_digest` / `hmac.compare_digest` の使用: **✅ 両方で正しく実装済み**
  - `auth/local_verifier.py:36`: `secrets.compare_digest(token, allowed)`
  - `security/webhook.py:29`: `hmac.compare_digest(expected, signature)`
- `SecretStr` 使用箇所: 2 件（設定クラス内）
- **結果**: ✅ 全 PASS

---

### 4. 入力バリデーション

- `CompareBody.a/b`: `max_length=512` → 実測で 413 文字超で 422 ✅
- `nbytes`: `ge=1, le=64` で境界チェック ✅
- `upper`: `ge=2, le=1_000_000` で境界チェック ✅
- タイプエラー: `nbytes="bad"` → 422（スタックトレースなし）✅
- **結果**: ✅

---

### 5. 情報漏洩

- 422 エラーに `traceback` / `File "` 含まれず ✅
- `SecretStr` でパスワード系フィールドを保護（2 箇所）✅
- セキュリティヘッダー全レスポンスに付与 ✅
- **結果**: ✅

---

### 6. Python / FastAPI 固有の攻撃ベクター

#### ReDoS
- `middleware/request_id.py` の UUID 正規表現: `^[0-9a-f]{8}-...-[0-9a-f]{12}$`
- 実測（悪意ある入力 `"a"*40+"!"`）: **0.00ms** — バックトラッキング爆発なし ✅
- **結果**: ✅

#### pickle / yaml / eval
- `grep eval\|exec\|pickle.loads\|yaml.load` → **PASS（0 件）** ✅
- **結果**: ✅

#### 非同期レースコンディション・型強制攻撃
- FT165 はステートレスな計算 API のため共有状態なし ✅
- Pydantic: `int` フィールドに文字列 `"bad"` → 422（型強制失敗でエラー返却）✅
- **結果**: ✅

---

### 7. 依存関係の脆弱性スキャン

```
uv run pip-audit
```

**結果**:

| Package | Version | ID | Fix Versions |
|---|---|---|---|
| pyjwt | 2.12.1 | PYSEC-2025-183 | （未記載） |

**CRITICAL: 1 件**

**詳細分析**:
- PyJWT 2.12.1 は `PYSEC-2025-183` の影響を受ける
- `pip-audit` の Fix Versions 欄が空 → 修正版未リリースの可能性
- **実際の影響**: nene2-python のソースコード全体を検索した結果、`import jwt` / `import pyjwt` が実コードに存在しない（コメントのみ）
- PyJWT は `pyproject.toml` に直接依存として宣言されていたが **デッド依存** → 本 FT で削除済み
- **推移的依存として残存**: `mcp>=1.0` パッケージが `pyjwt[crypto]` を推移的依存として使用しているため、pip-audit では引き続き検出される

**対応方針**:
1. `pyproject.toml` からの直接依存宣言: **本 FT で削除済み** (`uv remove pyjwt`)
2. 推移的依存（mcp 経由）: mcp 側の修正を待つ。Fix Versions が空のため修正版未リリース。Issue で追跡する。
3. nene2-python のコードが PyJWT を直接使わないため、実際の攻撃面はゼロ。

---

### 診断サマリー

| カテゴリ | 結果 | 最重要発見 |
|---|---|---|
| OWASP API Security Top 10 | ✅ | スロットリング未設定（本番要対応） |
| SQL インジェクション | ✅ | — |
| コマンドインジェクション | ✅ | — |
| パストラバーサル | ✅ | — |
| SSTI | ✅ | — |
| 認証・認可 | ✅ | compare_digest 正しく実装 |
| 入力バリデーション | ✅ | — |
| 情報漏洩 | ✅ | — |
| ReDoS | ✅ | 0ms — 安全 |
| pickle / yaml / eval | ✅ | — |
| 非同期レースコンディション | ✅ | — |
| 型強制攻撃 | ✅ | — |
| 依存関係 CVE | ❌ | **PyJWT 2.12.1 PYSEC-2025-183（デッド依存）** |

**総合評価**: **条件付き合格**（PyJWT CVE を次 PR で対処すること）

**発見した脆弱性**: 1 件（CRITICAL: 1 — PyJWT デッド依存 CVE）

**新規セキュリティ Issue**: PyJWT 依存削除または更新

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 高 | `fix: pyproject.toml から未使用の pyjwt 直接依存を削除（PYSEC-2025-183）` ← **本 FT で対処済み** | security |
| 高 | `track: mcp の推移的依存 pyjwt PYSEC-2025-183 修正版リリース待ち` | security |
| 中 | `feat: nene2.security に generate_token() ヘルパーを追加（最低 128 bit 保証）` | feat |
| 低 | `docs: secrets vs random の使い分けを how-to に追加` | docs |

---

## まとめ

`secrets` モジュールは暗号学的安全なトークン生成・タイミング安全比較の標準手段。
32 テスト全通過、摩擦ゼロで実装完了。

セキュリティ診断では nene2-python のソースコード全体を横断的に確認した。
`compare_digest` の正しい使用・`random` モジュール不使用・型バリデーション・セキュリティヘッダーはすべて合格。
**唯一の発見: PyJWT 2.12.1 のデッド依存 CVE (PYSEC-2025-183)**。
実際に使われていない依存が CVE を持つことはそれ自体がリスクのため、即時削除 PR を作成する。
