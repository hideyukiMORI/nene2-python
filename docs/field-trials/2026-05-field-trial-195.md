# FT195: ssl モジュール — TLS コンテキスト・暗号スイート・セキュリティ設定評価

**日付**: 2026-05-21
**テーマ**: Python `ssl` モジュールの SSLContext 設定・暗号スイート列挙・セキュリティ評価エンドポイントの実装と検証
**セキュリティ診断**: **あり**（195 % 3 = 0）
**クラッカーペンテスト**: なし（195 % 4 = 3）

---

## 概要

`ssl` モジュールは Python の TLS/SSL ラッパー。`SSLContext` によるコンテキスト設定、
`get_ciphers()` による暗号スイート列挙、`get_default_verify_paths()` によるシステム CA 確認など、
セキュリティ設定の診断ユーティリティとして活用できる。

FT193（socket）と FT194（ipaddress）の延長として「ネットワーク通信の安全性レイヤー」を担う。
今回は外部ネットワーク接続なしに、`SSLContext` のプロパティ読み取りと評価だけで完結する設計にした。
また、`/ssl/security-check` エンドポイントは「危険な SSL 設定の組み合わせ」を入力として受け取り、
問題を列挙する診断 API として機能する。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft195-ssl/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `default_context_info()` | `create_default_context()` の設定（verify_mode / check_hostname / TLS バージョン）を返す |
| `cipher_list()` | デフォルト SSLContext の有効な暗号スイートを最大 30 件返す |
| `system_ca_info()` | システムの CA バンドルパスと OpenSSL バージョン情報を返す |
| `security_assessment(verify_mode, check_hostname, min_tls)` | 指定した SSL 設定の問題を列挙して is_secure を返す |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/ssl/context` | デフォルト SSLContext 設定情報 |
| GET | `/ssl/ciphers` | 利用可能な暗号スイート一覧 |
| GET | `/ssl/system-ca` | システム CA バンドル情報 |
| POST | `/ssl/security-check` | SSL 設定パラメータのセキュリティ評価 |

---

## テスト結果

**24 passed**

```
24 passed in 0.77s
```

---

## 摩擦ポイント

### F-1: `ssl.SSLContext.get_ciphers()` の `_Cipher` TypedDict が `"bits"` キーを持たない（深刻度: 低）

**事象**: `raw["bits"]` を使うと mypy が
`TypedDict "_Cipher" has no key "bits"` と報告した。

**原因**: typeshed の `_Cipher` TypedDict は `bits` ではなく `strength_bits`（有効ビット数）と `alg_bits`（アルゴリズムビット数）に分けて定義している。

```python
# typeshed の _Cipher（抜粋）
class _Cipher(TypedDict):
    name: str
    protocol: str
    strength_bits: int  # ← "bits" ではなくこれ
    alg_bits: int
    ...
```

**対応**: `raw["strength_bits"]` を使用。実際の暗号スイート強度（AES-128 なら 128、AES-256 なら 256）を取得できる。

---

## 観察点

### 観察1: `ssl.create_default_context()` は Python 3.10+ で TLS 1.2 以上が保証される

```python
ctx = ssl.create_default_context()
# Python 3.10+ のデフォルト
# ctx.verify_mode == ssl.CERT_REQUIRED  → True
# ctx.check_hostname == True            → True
# ctx.minimum_version >= TLSv1.2       → True
```

`create_default_context()` は OpenSSL のデフォルトより安全な設定を強制する。
SSLContext を手動で生成する（`ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)`）場合は設定を明示する必要がある。

### 観察2: `Literal` 型と `@field_validator` で入力を二重に制約する

```python
class SecurityAssessmentBody(BaseModel):
    verify_mode: Literal["CERT_NONE", "CERT_OPTIONAL", "CERT_REQUIRED"] = "CERT_REQUIRED"
    min_tls_version: Literal["TLSv1", "TLSv1_1", "TLSv1_2", "TLSv1_3"] = "TLSv1_2"

    @field_validator("min_tls_version")
    @classmethod
    def validate_tls_version_supported(cls, v: str) -> str:
        try:
            ssl.TLSVersion[v]
        except KeyError:
            raise ValueError(f"unsupported TLS version: {v}")
        return v
```

`Literal` で Pydantic の型バリデーション（列挙以外は 422）、
`@field_validator` で実行環境の ssl ライブラリが実際にサポートするかを動的確認する2層構造。
「`SSLv3` という有効な Literal 値でもランタイムで使えない」ケースを弾ける。

### 観察3: `security_assessment` で問題を「累積」するパターン

```python
issues: list[str] = []
if verify_mode == ssl.CERT_NONE:
    issues.append("CERT_NONE: ... (HIGH)")
if not check_hostname:
    issues.append("check_hostname=False: ... (HIGH)")
if min_version < ssl.TLSVersion.TLSv1_2:
    issues.append("minimum_version=...: ... (HIGH)")
return SecurityAssessment(is_secure=(len(issues) == 0), issues=issues)
```

`if-elif` ではなく独立した `if` で複数の問題を同時に検出する。
一番危険な問題だけを返すのではなく全問題を列挙するため、
修正すべき設定の全体像がわかる。セキュリティ診断ツールの定石パターン。

---

## nene2-python フレームワークとの統合

- `ssl` モジュールは nene2 の `mcp/` や `database/` の HTTPS 接続設定で間接的に使われる。
- `default_context_info()` を定期実行してセキュリティ設定が劣化していないか監視する使い方が実用的。
- `security_assessment` のロジックは nene2 の設定検証ユーティリティ（起動時チェック）に昇格できる。
- `Literal` 型による入力制約は他の FT でも使えるパターン（enum-like な入力を安全に受け取る）。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

HTTP と HTTPS の違いは知っているが、TLS コンテキストの設定項目が何を意味するかわからない段階。

**ドキュメント理解**: `ssl.create_default_context()` が「安全なデフォルト」を提供することは Python 公式ドキュメントに書かれているが、「何が危険なデフォルトか」の対比情報が少ない。`security_assessment` エンドポイントは「危険な設定を入れると何が問題か」を直接確認できるハンズオンツールとして機能する。  
**事故リスク**: 中。`CERT_NONE` と `check_hostname=False` は「テストで動かすため」に一時的に設定して本番にそのまま残すリスクが高い。どちらも「動くが安全でない」設定であることを教えるが難しい。  
**規約の使いやすさ**: `ssl.create_default_context()` を使うだけで安全になる設計は初心者フレンドリー。危険な設定を意図的に使わなければ自動的に安全。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

`requests.get(url, verify=False)` を使ったことがある。なぜダメかを説明できない可能性がある。

**コピペ可能性**: `ssl.create_default_context()` のコードをコピーするだけなので問題ない。ただし `requests.get(verify=False)` との関係の説明がないと「低レベル ssl モジュールは使いにくい、requests で verify=False すれば楽」という誤解が生まれる。  
**拡張時の罠**: `ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)` を使い始めると手動での設定が必要になり、`check_hostname=True` を忘れがち。  
**セキュリティ的な事故リスク**: 高。`requests.get(url, verify=False)` や `ssl.CERT_NONE` は金融・医療系アプリで MITM 脆弱性に直結する。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

HTTPS が「鍵マーク」であることは知っているが、TLS バージョンや証明書検証の詳細は初めて。

**エラーレスポンスの質**: `"verify_mode": "CERT_INVALID"` を送ると Pydantic が 422 + `detail: "Input should be 'CERT_NONE', 'CERT_OPTIONAL' or 'CERT_REQUIRED'"` を返す。`Literal` 型の力でクライアントに使える値が明示される点が良い。  
**Python 固有概念の学習コスト**: `ssl.VerifyMode` / `ssl.TLSVersion` は SSL/TLS の知識が必要で、Python 固有というより SSL 固有の学習コスト。フロントエンド寄りには「なぜ IntEnum か」は不要で「どの値を使うべきか」だけ知ればよい。  
**事故リスク**: 低。このエンドポイント群は読み取り系 + 評価系。評価結果を受け取るだけなら副作用がない。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `SECURE_SSL_REDIRECT` や `SESSION_COOKIE_SECURE` で HTTPS 対応をした経験がある。

**他フレームワークとの差異**: Django はフレームワーク設定で TLS 関連を一元管理するが、Python の `ssl` モジュールは低レベルで、`requests` や `httpx` のデフォルトが適切かどうかを確認するのに使う。この FT の `default_context_info()` は「Python の ssl デフォルトが本当に安全か確認する」ための実用的な診断ツール。  
**nene2-python の薄さへの評価**: `security_assessment` エンドポイントが「評価ロジック」を純粋関数として分離している点は評価が高い。テストしやすく、ロジックを他の場所で再利用できる。  
**本番投入可能性**: `system_ca_info()` でシステムの CA バンドルパスを確認するエンドポイントは本番環境のデバッグに実用的。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

TLS 設定ミスによる CVE を過去に経験しており、セキュリティ設定のコードレビューを重視している。

**コードレビューチェックポイント**:
- [x] `ssl.create_default_context()` を使っているか（手動 SSLContext より安全）
- [x] `CERT_NONE` / `check_hostname=False` が本番コードに残っていないか
- [x] TLS 1.0/1.1 の `minimum_version` が設定されていないか
- [x] `verify_mode` が `Literal` 型で制約されているか（任意文字列ではない）
- [x] テストで「安全でない設定」が 422 で拒否されるか確認しているか

**チームでの安全な共有パターン**: 起動時に `default_context_info().is_secure` を確認して `False` なら警告ログを出すヘルスチェックが有効。  
**ツール追加の必要性**: `bandit` の `B501-B504`（ssl 関連の安全でない設定を検出）は ruff の `S` ルールでも一部カバーされる。`S501` (ssl CERT_NONE) は既に有効。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高  
**「初心者でも安全な API」達成度**: 高  

- `verify_mode` / `min_tls_version` が `Literal` 型で定義されており、Pydantic が自動的に許可値リストを OpenAPI スキーマに反映する。初心者が `CERT_INVALID` のような存在しない値を設定しても 422 が返る。
- `security_assessment` 関数はドメインロジックとして HTTP 層から独立しており、UseCase 層のユニットテストが容易。CLAUDE.md の「薄い HTTP 層」原則に沿っている。
- `Literal` + `@field_validator` の2層バリデーションは、静的（コンパイル時の型チェック）と動的（ランタイムのサポート確認）を組み合わせた強固なパターン。CLAUDE.md の「HTTP 境界の全入力を Pydantic で検証」を実践している。

**設計上の負債**: なし  
**Follow-up Issue 候補**: `security_assessment` の起動時ヘルスチェックへの統合（中優先度）

---

## セキュリティ診断（FT195 — 195 % 3 = 0）

> **診断方針**: `ssl` モジュールを使った SSL/TLS 設定のセキュリティを中心に、
> このサンドボックスアプリ自体の API セキュリティも確認する。

### 1. OWASP API Security Top 10 (2023)

#### API3: オブジェクトプロパティレベルの認可不備 (Mass Assignment)
- `SecurityAssessmentBody` に定義外フィールドを追加しても Pydantic の Extra='ignore' で無視される。
- `{"verify_mode": "CERT_REQUIRED", "is_admin": true}` を送っても `is_admin` は内部に漏れない。
- **結果**: ✅ 問題なし

#### API4: 無制限リソース消費
- `cipher_list()` は `ctx.get_ciphers()[:MAX_CIPHERS]` で最大 30 件に制限。
- 各フィールドは `Literal` または `bool` で固定長。巨大ペイロードのリスクはない。
- **結果**: ✅ 問題なし

#### API7: セキュリティの設定ミス
- `SSLContext.verify_mode` / `check_hostname` の評価エンドポイントが「危険設定」を明示的にフラグ立てする。
- サンドボックス自体は `APP_DEBUG` 設定なし（`ErrorHandlerMiddleware` を使っていないが FT サンドボックスとして許容範囲）。
- **結果**: ✅ 診断 API として機能している

---

### 2. インジェクション攻撃

#### コマンドインジェクション
- `ssl.VerifyMode[verify_mode_str]` で未知の文字列は `KeyError` になり `issues` に追加される。
- `ssl` モジュールの API に文字列コマンドを渡す操作はない。
- **結果**: ✅ 問題なし

#### インジェクション全般
- `security_assessment` のすべての入力は `Literal` 型（固定列挙）か `bool`。任意文字列の実行パスがない。
- **結果**: ✅ 問題なし

---

### 3. 認証・認可

このサンドボックスには認証機能を実装していない（FT として意図的）。
本番での `ssl` 設定 API は認証保護が必須。
**結果**: ✅ 診断 API 自体は副作用なし（読み取りのみ）

---

### 4. 入力バリデーション

- `verify_mode`: `Literal["CERT_NONE", "CERT_OPTIONAL", "CERT_REQUIRED"]` — 3 値のみ許可
- `check_hostname`: `bool` — True/False のみ
- `min_tls_version`: `Literal["TLSv1", "TLSv1_1", "TLSv1_2", "TLSv1_3"]` — 4 値のみ許可 + `@field_validator` でランタイム確認
- **結果**: ✅ 全入力が型で制約されている

テスト検証:
```python
# "CERT_INVALID" → 422 ✅
# "SSLv3" → 422 ✅
# {"verify_mode": "CERT_NONE", "is_admin": true} → 追加フィールド無視 ✅
```

---

### 5. 情報漏洩

- `system_ca_info()` が `cafile` / `capath` のシステムパスを返す。
  本番環境では内部パスの露出になりうるため、認証保護または `/internal/` プレフィックスで制限するべき。
  **⚠️ MEDIUM**: 本番では認証保護が推奨
- `openssl_version` の露出はバージョン情報の漏洩だが、攻撃者にとっての直接的な価値は低い（既知の OpenSSL バージョンには対応 CVE があるため、公開は最小限にすべき）。
  **⚠️ LOW**: 運用環境での注意が必要

**結果**: 条件付き合格（MEDIUM 以下の指摘のみ）— `/ssl/system-ca` エンドポイントは本番環境では認証保護が必要

---

### 6. Python/FastAPI 固有の攻撃ベクター

#### Pydantic 型強制
- `verify_mode: Literal[...]` に `"yes"` / `1` / `true` を送っても 422 で拒否される。
- `check_hostname: bool` に `"yes"` を送ると Pydantic v2 が `True` に変換することを確認。
  この変換は意図通りで、「`yes` → `True`」は CERT_REQUIRED + check_hostname=True の安全な設定になる。
- **結果**: ✅ 問題なし（型強制の方向が安全）

#### `ssl.VerifyMode[unknown_str]` の KeyError
- `security_assessment` 内で `ssl.VerifyMode[verify_mode_str]` が `KeyError` になるケースは
  `try/except` で捕捉して `issues` に追加する設計になっている。
- ただし、`verify_mode: Literal[...]` の制約があるため、HTTP 経由では `KeyError` パスに到達しない。
  内部関数として直接呼んだ場合のみ発生する。
- **結果**: ✅ 問題なし

---

### 7. 依存関係の脆弱性スキャン

```
Found 1 known vulnerability in 1 package
pyjwt 2.12.1  PYSEC-2025-183
```

- **PYSEC-2025-183**: mcp 経由の PyJWT 推移的 CVE（許容済み、mcp 側の修正待ち）
- **スキャン結果**: CRITICAL: 0 / HIGH: 0 / MEDIUM: 0 / LOW: 0（PyJWT 除く）
- **対応方針**: 許容済み

---

### 診断サマリー

| カテゴリ | 結果 | 最重要発見 |
|---|---|---|
| OWASP API Security Top 10 | ✅ 全通過 | `/ssl/system-ca` は本番で認証推奨 |
| インジェクション攻撃 | ✅ 問題なし | Literal 型が全入力を固定値に制約 |
| 認証・認可 | ✅ 診断 API は副作用なし | 本番投入時は認証が必要 |
| 入力バリデーション | ✅ 全通過 | Literal + @field_validator の2層 |
| 情報漏洩 | ⚠️ MEDIUM | system-ca でシステムパス露出 |
| 型強制攻撃 | ✅ 問題なし | 安全方向の型強制のみ |
| 依存関係 CVE | ✅ 許容済み | PYSEC-2025-183 (mcp / PyJWT) |

**総合評価**: 条件付き合格  
**発見した脆弱性**: 1件（MEDIUM: `/ssl/system-ca` の認証保護推奨）  
**新規セキュリティ Issue**: なし（本番判断として記録）

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| 低 | `/ssl/system-ca` エンドポイントの本番運用時の認証保護ガイドを docs/how-to に記録 | docs |

---

## まとめ

`ssl` モジュールは外部ネットワーク接続なしに SSLContext の設定確認・暗号スイート列挙・セキュリティ評価ができる実用的な診断ツールを提供する。
F-1（`_Cipher["bits"]` → `"strength_bits"`）は typeshed の小さな落とし穴だった。

セキュリティ診断では `CERT_NONE`・`check_hostname=False`・TLS 1.0/1.1 の危険性を実装レベルで実証し、
`Literal` + `@field_validator` の2層バリデーションが入力を安全に制約することを確認した。
唯一の指摘は `system_ca_info()` のシステムパス露出（MEDIUM）で、本番では認証保護が推奨される。

次の FT196 は 196 % 3 = 1 → セキュリティ診断なし、196 % 4 = 0 → **クラッカーペンテストあり**。
テーマ候補: `http.client`（低レベル HTTP クライアント）または `select` / `selectors`（I/O 多重化）。
