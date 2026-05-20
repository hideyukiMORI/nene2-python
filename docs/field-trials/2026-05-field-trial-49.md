# Field Trial 49: AppSettings 実運用検証

**日付**: 2026-05-20
**バージョン**: v1.8.8 時点
**テーマ**: `AppSettings` の環境変数オーバーライド・バリデーション・`db_url` プロパティ・SecretStr の動作を確認

---

## 概要

`AppSettings` の全主要機能（環境変数オーバーライド・バリデーター・`db_url` プロパティ生成・
SecretStr によるパスワード保護・リスト型環境変数の設定方法）を確認した。

---

## 実装内容

`/home/xi/docker/nene2-python-FT/ft49-app-settings/` に以下を作成:

- **`test_settings.py`** — AppSettings の全機能確認 (13 件)

**テスト結果**: 13 件全通過 ✅

---

## 摩擦点

### FP49-1: db_password は SecretStr のため repr に平文が出ない

**分類**: 摩擦なし（良い設計の確認）

`db_password: SecretStr` のため、`repr(settings)` や `print(settings)` で
パスワードが平文で出力されない。ログに誤ってパスワードが漏洩しない設計。

実際の値が必要な場合は `settings.db_password.get_secret_value()` を使う。
`db_url` プロパティが内部で呼んでいるので、通常は直接呼ぶ必要はない。

**判断**: セキュリティ上の重要な設計。

---

### FP49-2: リスト型環境変数は JSON 配列形式で設定する

**分類**: 軽微な摩擦（注意喚起）

`bearer_tokens`・`api_keys`・`cors_origins` などのリスト型フィールドを
環境変数で設定する場合、pydantic-settings は JSON 配列形式を期待する:

```bash
# OK: JSON 配列形式
export BEARER_TOKENS='["token-a", "token-b"]'

# NG: カンマ区切り（動作しない）
export BEARER_TOKENS="token-a,token-b"
```

`LocalTokenVerifier.from_env()` (FT11) はカンマ区切りをサポートしているが、
`AppSettings.bearer_tokens` 自体は JSON 配列形式が必要。

**判断**: pydantic-settings の仕様通り。NENE2 の `README` や設定リファレンスドキュメントに
明記する価値がある。

---

### FP49-3: app_env は "local" / "test" / "production" のみ

**分類**: 摩擦なし（設計の確認）

`validate_app_env` バリデーターで "staging" など他の値を拒否する。
デプロイ環境を厳密に 3 種類に限定することで設定ミスを防ぐ。

---

### FP49-4: log_level は大文字に自動正規化される

**分類**: 摩擦なし（良い設計の確認）

`validate_log_level` バリデーターで "debug" → "DEBUG" に変換される。
大文字・小文字を気にせずに設定できる。

---

## フレームワーク変更

なし（全て設計通りの挙動）

ドキュメント追記を検討:
- `docs/reference/configuration.md` にリスト型環境変数の設定方法を明記

---

## 関連

- `nene2.config.AppSettings`
- FT11 (LocalTokenVerifier.from_env, v1.4.0)
- FT26 (setup_logging log_level パラメータ, v1.8.1)
