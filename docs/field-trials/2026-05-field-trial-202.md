# FT202: hmac モジュール — HMAC 計算・検証・timing-safe 比較

**日付**: 2026-05-22
**テーマ**: Python `hmac` モジュールの HMAC 計算・検証・`compare_digest` タイミング安全比較の実装と検証
**セキュリティ診断**: なし（202 % 3 = 1）
**クラッカーペンテスト**: なし（202 % 4 = 2）

---

## 概要

`hmac` は Python 標準ライブラリの HMAC（Hash-based Message Authentication Code）実装モジュール。
メッセージ認証・API 署名・Webhook 署名検証など、「鍵を持つハッシュ」が必要な場面で使われる。
FT201 の hashlib フィールドトライアルで `hmac.compare_digest` の存在が明らかになったため、
今回は `hmac` モジュール全体を主題として掘り下げた。

---

## 実装したサンプルアプリ

**場所**: `/home/xi/docker/nene2-python-FT/ft202-hmac/`

### 主要機能

| 関数/クラス | 概要 |
|---|---|
| `compute_hmac(key, message, digestmod)` | テキスト HMAC を計算して `HmacResult` を返す |
| `compute_hmac_bytes(key, message, digestmod)` | バイト列 HMAC を計算する |
| `verify_hmac(key, message, expected_hex, digestmod)` | timing-safe に HMAC を検証 |
| `is_digest_safe_equal(a, b)` | `hmac.compare_digest` のラッパー — timing-safe 文字列比較 |
| `HmacResult` | algorithm / hex_digest / digest_size を保持する frozen dataclass |
| `VerifyResult` | algorithm / is_valid を保持する frozen dataclass |

### HTTP エンドポイント

| メソッド | パス | 概要 |
|---|---|---|
| POST | `/hmac/compute` | 秘密鍵とメッセージから HMAC を計算する |
| POST | `/hmac/verify` | HMAC を timing-safe に検証する（200 + is_valid） |

---

## テスト結果

**24 passed**

```
24 passed in 0.08s
```

---

## 摩擦ポイント

**今回の FT では実装上の摩擦はゼロだった。**

FT201 で `hmac.compare_digest` の存在をすでに発見・記録していたため、
今回は `hmac.new()` → `.hexdigest()` の流れをそのまま実装できた。
`import hashlib` を `demos.py` と `test_app.py` に余分に書いて ruff F401 が出たが、
`ruff --fix` で即座に修正された。

---

## 観察点

### 観察1: `hmac.new()` の `digestmod` はモジュールまたは文字列どちらでも受け取る

```python
import hashlib, hmac

# 文字列で指定（推奨・可読性高い）
h = hmac.new(b"key", b"msg", digestmod="sha256")

# モジュール関数で指定（古い使い方）
h = hmac.new(b"key", b"msg", digestmod=hashlib.sha256)
```

Python 3.4 以降どちらも動くが、文字列指定の方がシリアライズしやすく API 設計に向いている。

### 観察2: `hmac.new()` の第2引数（msg）は省略可能

```python
h = hmac.new(b"key", digestmod="sha256")
h.update(b"chunk1")
h.update(b"chunk2")
digest = h.hexdigest()
```

ストリーミング更新パターン。大きなデータを分割処理する場合に有効。
今回のエンドポイントは全体を一度に受け取るためこのパターンは使用しなかった。

### 観察3: `hmac.compare_digest` は bytes でも str でも動く

```python
hmac.compare_digest("abc", "abc")   # → True (str)
hmac.compare_digest(b"abc", b"abc") # → True (bytes)
hmac.compare_digest("abc", b"abc")  # → TypeError: 型を混在できない
```

引数の型を統一する必要がある。`hexdigest()` は `str` を返すため、
比較には一方を `str` に揃えるか両方を `bytes` にする（`.digest()` を使う）かを選ぶ。
今回は両方 `str` に統一した。

---

## nene2-python フレームワークとの統合

- `DigestMod = Literal["sha256", "sha512", "sha3_256", "sha3_512"]` で
  `md5` / `sha1` を許可アルゴリズムから除外。セキュリティ強化。
- `verify_hmac` エンドポイントは 200 + `is_valid` を返す（例外でなく Result 型）。
  「HMAC が合わない」は正常業務フロー（リプレイ攻撃・改ざん検知）であり、422 は適切でない。
- `key` フィールドに `max_length=512`、`message` に `max_length=65536` を設定。
  HMAC の鍵はどんな長さでも動くが、入力の際限なし受け入れは DoS になり得るため制限が必要。

---

## Developer Experience (DX) Review

### ペルソナ1: 初心者（Python 歴1年・独学中・女性・バックエンド志望）

Webhook 署名検証機能を実装しようとしている。

**ドキュメント理解**: `hmac.new(key, msg, digestmod).hexdigest()` のパターンはシンプル。
「なぜ `hashlib` でなく `hmac` を使うのか」（鍵付きハッシュの概念）は説明が必要。
「なぜ `==` でなく `compare_digest` を使うのか」（タイミング攻撃）も初学者には分かりにくい。  
**事故リスク**: 中。`hmac.compare_digest` を使わず `==` 比較するコードを書きやすい。
`is_digest_safe_equal()` のラッパー関数を共通ライブラリとして提供するパターンが有効。  
**規約の使いやすさ**: `compute_hmac()` / `verify_hmac()` のペアは分かりやすい。

### ペルソナ2: ロースキル経験者（Python 歴3-4年・スクリプト系・男性・SES）

GitHub の Webhook 署名検証コードをコピーしてきた経験がある。

**コピペ可能性**: `verify_hmac()` はそのままコピーして使える。
`is_digest_safe_equal()` の重要性が理解できない場合に「これいらなくね？」と削除するリスクあり。  
**拡張時の罠**: `digestmod="md5"` を渡すと `ValueError` になる（許可リスト制限）ことを
事前に知らないとデバッグに詰まる可能性。  
**セキュリティ的な事故リスク**: 中（`==` 比較への置き換えリスク）。

### ペルソナ3: フロントエンド寄り経験者（React/TS 歴4年・バックエンド転向中・ノンバイナリ）

GitHub / Stripe などの Webhook の署名検証を実装した経験がある。

**エラーレスポンスの質**: 検証失敗が 200 + `is_valid: false` で返る設計は、
Stripe 等の「検証失敗は通常フロー」という設計と一致していて直感的。  
**Python 固有概念の学習コスト**: `hmac.compare_digest` が Node.js の `crypto.timingSafeEqual` と
同等であると分かれば理解しやすい。  
**事故リスク**: 低。

### ペルソナ4: バックエンド経験者（Django/FastAPI 歴5-6年・男性・リードエンジニア）

HMAC ベースの API 署名を実装する経験がある。

**他フレームワークとの差異**: Django の `django.utils.crypto.constant_time_compare()` が
内部で `hmac.compare_digest` を使っているため、Python 標準レベルでの実装を把握する価値がある。  
**nene2-python の薄さへの評価**: `hmac.new` を薄くラップするだけで、フレームワーク依存がない点は高評価。  
**本番投入可能性**: Webhook 署名検証・API キー検証に十分使える設計。

### ペルソナ5: シニアエンジニア（設計・コードレビュー担当・女性・10-12年）

セキュリティポリシーに基づいたコードレビューを担当する。

**コードレビューチェックポイント**:
- [ ] HMAC 比較が `==` でなく `hmac.compare_digest` を使っているか
- [ ] `digestmod` が許可リスト（`Literal` 型）で制限されているか（md5/sha1 除外）
- [ ] `key` フィールドに `max_length` が設定されているか

**チームでの安全な共有パターン**: `verify_hmac()` を唯一の検証エントリポイントとし、
直接 `hmac.new().hexdigest() == expected` を書くことを禁止するルールが有効。  
**ツール追加の必要性**: ruff S（bandit）の `S312` が `==` による HMAC 比較を検出可能。

### ペルソナ6: 設計者・ポリシー照合（nene2-python 設計ポリシー目線）

**ポリシー達成度**: 高。CLAUDE.md の「タイミング攻撃: `hmac.compare_digest()` を使用」が
正しく実装された。`Literal` 型でアルゴリズム制限も実現。  
**「初心者でも安全な API」達成度**: 中。`compare_digest` の重要性が API レベルでは見えにくい。
コードコメントや HOWTO があると理解しやすくなる。  
**設計上の負債・ドキュメント不足**: `is_digest_safe_equal()` のラッパー関数が
nene2-python コアに入ると初心者の事故リスクが下がる可能性がある。  
**Follow-up Issue 候補**: なし（デモスコープで十分）

---

## Follow-up Issues

| 優先度 | タイトル | 種別 |
|---|---|---|
| — | なし | — |

---

## まとめ

`hmac` モジュールは `hashlib` の上に薄く乗った鍵付きハッシュ実装。
FT201 での `hmac.compare_digest` 発見を踏まえて実装に入ったため、摩擦はほぼゼロだった。

設計上の最重要ポイントは「HMAC 検証の比較は必ず `hmac.compare_digest` を使う」点で、
これは初心者が最も見落としやすいセキュリティ的な落とし穴でもある。
FT202 のサンプルコードは `verify_hmac()` 関数にこのパターンを内包し、
呼び出し側が意識しなくて済む設計とした。

次の FT203 は `203 % 3 = 2` → 診断なし、`203 % 4 = 3` → ペンテストなし。
