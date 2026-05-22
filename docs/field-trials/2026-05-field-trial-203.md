# FT203: secrets モジュール — セキュア乱数・トークン生成・OTP

**日付**: 2026-05-22
**テーマ**: Python `secrets` モジュールのセキュア乱数生成・トークン生成・OTP 生成の実装と検証
**セキュリティ診断**: なし（203 % 3 = 2）
**クラッカーペンテスト**: なし（203 % 4 = 3）

---

## 概要

`secrets` モジュールは Python 3.6 で追加された暗号論的に安全な乱数生成モジュール。
CLAUDE.md のセキュリティポリシーに「セキュア乱数: `secrets` モジュール（`random` モジュール禁止）」と明記されており、
実際にどのような API を提供するかをフィールドトライアルで検証した。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft203-secrets/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `generate_hex_token(byte_length)` | `secrets.token_hex()` で16進数トークンを生成して `TokenResult` を返す |
| `generate_urlsafe_token(byte_length)` | `secrets.token_urlsafe()` で URL-safe Base64 トークンを生成する |
| `generate_otp(length, digits_only)` | `secrets.choice()` で OTP を生成して `OtpResult` を返す |
| `TokenResult` | token / byte_length / char_length を保持する frozen dataclass |
| `OtpResult` | otp / length / digits_only を保持する frozen dataclass |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| GET | `/tokens/hex` | 16進数トークンを生成（`?byte_length=32`） |
| GET | `/tokens/urlsafe` | URL-safe Base64 トークンを生成 |
| POST | `/otp/generate` | 数字または英数字 OTP を生成（デフォルト6桁） |

---

## テスト結果

**27 passed**

```
27 passed in 0.31s
```

---

## 摩擦ポイント

**今回の FT では実装上の摩擦はゼロだった。**

`secrets` モジュールは `random` モジュールと同等の関数名パターンを持ちながら、
内部で OS の CSPRNG（`os.urandom()`）を使用するシンプルな設計。
CLAUDE.md に「`random` モジュール禁止、`secrets` モジュールを使う」と明記されていたため、
初めから正しい API を選択できた。

---

## 観察点

### 観察1: `token_hex(n)` のトークン長は `n * 2` 文字

```python
import secrets

token = secrets.token_hex(32)
print(len(token))  # → 64（32バイト × 2文字/バイト）
```

ドキュメントに明記されているが、「32バイトのトークン」というと「32文字」と混同しやすい。
実装者が「短い」と感じる場合は、バイト数ではなく文字数で考えていることが多い。

### 観察2: `token_urlsafe(n)` はパディングなし Base64URL

```python
token = secrets.token_urlsafe(32)
assert "=" not in token  # パディングなし
assert "+" not in token  # URL-safe（+ の代わりに -）
assert "/" not in token  # URL-safe（/ の代わりに _）
```

FT200（base64）で学んだパディング問題とは無関係。
`secrets.token_urlsafe()` は `base64.urlsafe_b64encode(secrets.token_bytes(n)).rstrip(b"=").decode()` 相当だが、
内部実装を気にせず使えるため DX は高い。

### 観察3: `secrets.choice()` は `random.choice()` の安全な代替

```python
import secrets

charset = "0123456789"
otp = "".join(secrets.choice(charset) for _ in range(6))
```

`random.choices(charset, k=6)` との違い:
- `random.choices()` は統計的ランダム（線形合同法）— **暗号用途禁止**
- `secrets.choice()` は CSPRNG — **OTP・認証コード生成に適切**

### 観察4: `secrets` には `compare_digest` がない

FT201（hashlib）で `hmac.compare_digest` が `hashlib` にないことを発見したが、
同様に `secrets` にも `compare_digest` はない。
timing-safe 比較は `hmac.compare_digest()` が唯一の正解。

```python
# ✅ 正しい timing-safe 比較
import hmac
hmac.compare_digest(user_input, expected)

# ❌ secrets には compare_digest がない
import secrets
secrets.compare_digest(...)  # AttributeError
```

---

## nene2-python フレームワークとの統合

- `byte_length` に `ge=8, le=64` の制限を設定。
  最小 8 バイト（64 ビット強度）を下回るトークンはブルートフォース耐性が低い。
- OTP `length` に `ge=4, le=32` の制限を設定。
  4 桁未満の OTP は予測可能（10,000 通り）。
- `secrets.SystemRandom` は今回使用しなかった。
  `random.Random` の CSPRNG 版だが、`secrets.token_*` / `secrets.choice()` で十分。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

メール認証用の OTP 生成機能を実装しようとしている。

**ドキュメント理解**: `secrets.token_hex(32)` / `secrets.token_urlsafe(32)` / `secrets.choice(charset)` の 3 パターンは覚えやすい。
「なぜ `random.randint()` ではダメなのか」の説明が必要。  
**事故リスク**: 高。`random` モジュールを使ってしまうリスクが高い。
CLAUDE.md の `random` 禁止ポリシーが効果的な防壁になる。  
**規約の使いやすさ**: `generate_otp()` という関数名は意図が明確。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

「トークンを生成してね」と言われたときに `random.token_hex()` と書いてしまうリスクがある（実在しない）。

**コピペ可能性**: Stack Overflow の古いコードに `random.random()` を使ったトークン生成があり、コピペしやすい。  
**拡張時の罠**: `secrets.choice()` と `random.choices()` の混同。後者は **複数選択できる便利関数** として認識されがち。  
**セキュリティ的な事故リスク**: 高。`random` → `secrets` の置き換えを怠るリスク。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

Node.js の `crypto.randomBytes()` / `crypto.randomUUID()` との対応が分かればすぐ使える。

**エラーレスポンスの質**: 422 バリデーションエラー（`byte_length` 範囲外）は Pydantic が自動生成するため適切。  
**Python 固有概念の学習コスト**: `secrets.token_urlsafe()` は Node.js の `nanoid` / `crypto.randomBytes().toString('base64url')` と同等。対応関係が明確。  
**事故リスク**: 低。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Django の `secrets.token_hex()` を使った CSRF トークン生成を知っている。

**他フレームワークとの差異**: Django の `get_random_string()` は `secrets.choice()` ベースで同等。  
**nene2-python の薄さへの評価**: `secrets` を直接使ってラップを最小にしている点は高評価。
ラッパーが増えるほど「どこで何が変わるか」が分かりにくくなる。  
**本番投入可能性**: OTP・セッショントークン・API キー生成に十分使える。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

セキュリティポリシーのコードレビューを担当する。

**コードレビューチェックポイント**:
- [ ] `random` モジュールが使われていないか（ruff S311 で自動検出可能）
- [ ] `secrets.choice()` を使っているか（`random.choice()` でないか）
- [ ] トークン長が 8 バイト（64 ビット）以上か
- [ ] OTP が 4 桁以上か

**チームでの安全なパターン**: `generate_otp()` / `generate_hex_token()` を共通ライブラリとして提供し、
直接 `secrets` を呼ぶことを禁止するルールが有効。  
**ツール追加の必要性**: `ruff S311`（`random` の暗号用途使用を検出）が有効。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高。CLAUDE.md の「セキュア乱数: `secrets` モジュール（`random` 禁止）」が正しく実装された。  
**「初心者でも安全な API」達成度**: 中。`generate_otp()` / `generate_hex_token()` のラッパーで初心者の事故リスクを低減できる。
ただし `secrets` の直接使用を止める手段がないため、CLAUDE.md の教育的記述が重要。  
**設計上の負債・ドキュメント不足**: `ruff S311` の有効化を `pyproject.toml` に追記すべき可能性あり。
現在の ruff 設定に `S`（bandit）は含まれているため、既に有効かもしれない（要確認）。  
**Follow-up Issue 候補**: なし（デモスコープで十分）

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| — | なし | — |

---

## まとめ

`secrets` モジュールは `random` モジュールの暗号安全版として設計された薄いラッパー。
`token_hex()` / `token_urlsafe()` / `choice()` の 3 関数を覚えるだけで、
セッショントークン・OTP・API キー・パスワードリセットトークンなど
ほぼすべてのセキュア乱数ユースケースをカバーできる。

最大の教育効果は「`random` ではなく `secrets` を使う理由を知ること」。
ruff S311 による `random` の暗号用途検出と CLAUDE.md の禁止ポリシーで、
チーム全体のセキュリティ水準を担保できる。

次の FT204 は `204 % 3 = 0` → セキュリティ診断あり、`204 % 4 = 0` → クラッカーペンテストあり。
