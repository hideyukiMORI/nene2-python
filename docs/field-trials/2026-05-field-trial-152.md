# Field Trial 152: hashlib モジュール

## テーマ

`hashlib.md5/sha1/sha256/sha512/blake2b/blake2s`, `hashlib.new()`,
`hashlib.pbkdf2_hmac`, `hashlib.algorithms_available/guaranteed`,
`hmac.new()`, `hmac.compare_digest()` を FastAPI で検証する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft152-hashlib/` に以下を実装:

- `hash_md5/sha256/sha512/blake2b/blake2s()` — 各アルゴリズムのハッシュ計算
- `hash_with_algorithm()` — `hashlib.new()` で動的にアルゴリズムを選択
- `hash_incrementally()` — `update()` でチャンク単位にデータを追加
- `hash_bytes()` — バイト列のハッシュ計算
- `hash_password_pbkdf2()` — `pbkdf2_hmac` でパスワードハッシュ（salt + 10万回イテレーション）
- `verify_password_pbkdf2()` — `hmac.compare_digest()` でタイミング安全な検証
- `compute_hmac()` / `verify_hmac()` — HMAC の計算と検証
- `list_algorithms()` — `algorithms_available` と `algorithms_guaranteed` を返す
- HTTP エンドポイント 7 本
- 30 テスト全通過（摩擦0件）

## テスト結果

初回: 30 テスト全通過。摩擦なし。

## 摩擦なし

今回はブロッカーとなる摩擦なし。`hmac.compare_digest()` の使い方が分かりやすく整理できた。

## 観察

### O1: `hashlib.new()` で動的にアルゴリズムを選択できる

```python
h = hashlib.new("sha256", b"hello")
h.hexdigest()  # SHA-256 ハッシュ

# 以下と同等
hashlib.sha256(b"hello").hexdigest()
```

`hashlib.new(name)` でアルゴリズム名を文字列で渡せるため、
設定ファイルや API パラメーターで動的にアルゴリズムを切り替えられる。
存在しないアルゴリズム名は `ValueError` を送出する。

### O2: `update()` でインクリメンタルにデータを追加できる

```python
h = hashlib.sha256()
h.update(b"hello")
h.update(b" world")
h.hexdigest()  # sha256(b"hello world") と同一
```

大きなファイルをチャンク単位で読み込んでハッシュを計算する際に有用。
`update()` の呼び出し結果は連結したバイト列のハッシュと等価。

### O3: `pbkdf2_hmac` でパスワードハッシュを実装できる

```python
import secrets

salt = secrets.token_bytes(32)  # 32バイトのランダムsalt
dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations=100_000)
# → 導出キー (bytes)
```

`iterations=100_000` は OWASP 推奨値（2024年時点では 600_000 推奨）。
`salt` は毎回 `secrets.token_bytes()` で新規生成してパスワードとともに保存する。

### O4: `hmac.compare_digest()` でタイミング攻撃を防ぐ

```python
import hmac

def verify_password(stored_hash: str, computed_hash: str) -> bool:
    # NG: stored_hash == computed_hash  # 文字列長で計算時間が変わる
    return hmac.compare_digest(stored_hash, computed_hash)  # OK: 定時間比較
```

`==` 演算子は一致しない最初の文字で返るためタイミング攻撃に脆弱。
`hmac.compare_digest()` は常に全文字を比較して定時間で結果を返す。

### O5: `algorithms_guaranteed` と `algorithms_available` の違い

```python
hashlib.algorithms_guaranteed  # すべての Python 実装で保証されるアルゴリズム集合
hashlib.algorithms_available   # 現在の OpenSSL 等で利用可能なアルゴリズム集合（上位集合）
```

`algorithms_guaranteed` は `md5`, `sha1`, `sha224`, `sha256`, `sha384`, `sha512`,
`blake2b`, `blake2s` を含む。
`algorithms_available` はシステムの OpenSSL に依存してさらに多くを含む可能性がある。

### O6: BLAKE2 は SHA-2 より高速で衝突耐性がある

```python
# BLAKE2b: 64 バイト出力（デフォルト）、digest_size で調整可
hashlib.blake2b(b"hello", digest_size=32).hexdigest()  # 64 hex chars

# BLAKE2s: 32 バイト出力（デフォルト）、32 ビット最適化
hashlib.blake2s(b"hello", digest_size=16).hexdigest()  # 32 hex chars
```

`key` 引数でキー付きハッシュ（HMAC 相当）も可能:
`hashlib.blake2b(b"hello", key=b"secret")`.

## まとめ

FT152 は摩擦ゼロ。`hashlib` は `hashlib.new()` による動的選択、
`update()` によるインクリメンタル処理、`pbkdf2_hmac` によるパスワードハッシュを
提供する。`hmac.compare_digest()` はタイミング攻撃耐性のある検証に必須。
