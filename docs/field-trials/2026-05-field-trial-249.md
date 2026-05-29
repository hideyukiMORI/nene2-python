# FT249: hmac — new / compare_digest（署名検証・タイミング攻撃対策）

**日付**: 2026-05-29
**テーマ**: Python `hmac` モジュールのメッセージ認証と定数時間検証の実装と検証
**セキュリティ診断**: 🔒 あり（249 % 3 = 0）
**クラッカーペンテスト**: なし（249 % 4 = 1）

---

## 概要

`hmac` は鍵付きハッシュによるメッセージ認証コード（MAC）を提供する。HTTP API でラップし、Webhook 署名の生成・検証パターンを検証した。FT222（hashlib・パスワードハッシュ）と対をなし、**鍵を知る者だけが正しい署名を作れる**ことと、検証での**定数時間比較**（タイミング攻撃対策）が要点。

| API | ユースケース |
|---|---|
| `hmac.new(key, msg, "sha256").hexdigest()` | HMAC-SHA256 署名生成 |
| `hmac.compare_digest(a, b)` | 定数時間比較（タイミング攻撃対策） |

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft249-hmac/`

| 関数 | 概要 |
|---|---|
| `sign_message()` | HMAC-SHA256 署名を生成 |
| `verify_signature()` | `compare_digest` で定数時間検証 |

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/hmac/sign` | 署名生成 |
| POST | `/hmac/verify` | 署名を定数時間検証 |

---

## 摩擦点

### F-1: 検証は `==` ではなく `hmac.compare_digest`

**観察**: 署名照合を `expected == provided` で書くと、先頭から逐次比較・早期 return するため一致バイト数で応答時間が変わり、攻撃者が署名を 1 バイトずつ推測できる（タイミング攻撃）。

**対処**: `hmac.compare_digest(expected, provided)` を使う。ソース中の `==` は**コメント（「== ではなく」）のみ**で実比較は compare_digest であることを確認（FT222 と同じ grep 誤検知に注意）。

### F-2: digestmod は sha256（md5/sha1 を使わない）

**観察**: `hmac.new(key, msg)` の digestmod を省略するとエラー、または弱いアルゴリズムを選ぶ余地が出る。HMAC-MD5 は理論的攻撃があり非推奨。

**対処**: `DIGEST_ALGORITHM = "sha256"` 固定。アルゴリズムをユーザー入力から取らない。

### F-3: 不正署名は例外ではなく `valid=False`

**観察**: 検証で `provided` が hex でない・長さが違う場合でも、`compare_digest` は例外を出さず False を返す（長さの異なる入力も安全に処理）。例外にすると「形式が違う」と「鍵が違う」を区別され情報になる。

**対処**: 不正署名は `valid=False`（200）で一律扱い。`not-hex`・空文字も False。署名長は上限化（過大入力は 422）。

---

## セキュリティ診断結果

| カテゴリ | 例 | 結果 |
|---|---|---|
| アルゴリズム強度 | digestmod | **hmac-sha256**（md5/sha1 不使用） |
| タイミング攻撃 | 比較方法 | **compare_digest**（== はコメントのみ） |
| 改ざん検出: メッセージ | `amount=100`→`amount=9999` | **valid=False** |
| 改ざん検出: 鍵 | 攻撃者の鍵 | **valid=False** |
| 改ざん検出: 署名切り詰め | 先頭 32 文字 | **valid=False** |
| 改ざん検出: 1 文字反転 | 先頭フリップ | **valid=False** |
| 不正署名 | `not-hex` / 空 | **200 valid=False**（例外漏れなし） |
| 過大署名 | 400 文字 | **422** |
| 空鍵 / 過大メッセージ | — | **422** |
| セキュリティヘッダー | — | 付与あり |

**総合評価: 合格**

HMAC-SHA256 + `compare_digest` で改ざん（メッセージ・鍵・署名のいずれの変更）を全検出し、タイミング攻撃・弱アルゴリズム・情報漏洩を防止。Webhook 署名検証の標準パターンとして妥当。

---

## テスト結果

```
7 passed in 0.86s
```

`pytest`, `mypy --strict`, `ruff check`, `ruff format --check`, `pip-audit` すべて通過。

---

## DX Review — 6 ペルソナ

### 1. 初心者（Python 歴1年・独学中・女性・バックエンド志望）

「鍵で署名して検証」は理解しやすい。compare_digest を使う理由（タイミング攻撃）は学ぶ必要。

**ドキュメント理解**: なぜ `==` ではダメかをコメントで明示。
**事故リスク（中）**: `==` で署名照合してしまう。
**規約の使いやすさ**: sign→verify の往復が明快。

### 2. ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

Webhook（Stripe/GitHub）の署名検証で使う。`==` 照合・md5 利用の事故が起きやすい。

**コピペ可能性**: sign/verify は流用可。
**拡張時の罠**: `==` 比較・digestmod 弱化。
**事故リスク（中）**: タイミング攻撃。

### 3. フロントエンド寄り（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

`crypto.createHmac` に対応。署名検証はサーバー側の責務と理解。

**エラーレスポンスの質**: 過大入力は 422、検証失敗は valid=False。
**Python 固有概念**: compare_digest の定数時間性。
**事故リスク（低）**: 既定で堅い。

### 4. バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

Webhook 署名・API 署名で定番。鍵は環境変数/Secrets Manager、`SecretStr` 管理が望ましい。nene2 には `verify_hmac_signature` もある。

**他フレームワークとの差異**: 各プロバイダの署名検証も compare_digest 相当。
**nene2 の薄さへの評価**: sha256 固定・compare_digest 採用が適切。
**事故リスク（低）**: 診断で全改ざん検出。

### 5. シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

**コードレビューチェックポイント**:
- 署名照合が `==` ではなく `compare_digest` か（タイミング攻撃）。
- digestmod が sha256 以上か（md5/sha1 不可）。
- 鍵を `SecretStr`/環境変数で管理しログに出していないか（FT220）。
- 不正署名を例外ではなく valid=False で一律扱いしているか（情報漏洩）。

**チームでの安全なパターン**: 署名検証は共通関数（nene2.security.verify_hmac_signature）に集約。
**事故リスク（低）**: 診断を回帰化。

### 6. 設計者（nene2-python 設計ポリシー目線）

**CLAUDE.md ポリシー整合性**: `secrets`/HMAC 思想と整合。Pydantic 制限・`ValidationException` 変換・`logging` 使用は準拠。`nene2.security.verify_hmac_signature` の存在とも一貫。
**初心者でも安全な API 達成度**: sha256 固定・compare_digest を関数内に隠蔽し、誤用の余地を排除。
**改善提案**: 鍵を `SecretStr` で受ける版・タイムスタンプ付き署名（リプレイ攻撃対策）を how-to に追記し、FT222/FT203 と相互リンクする。
