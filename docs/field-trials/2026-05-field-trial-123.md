# Field Trial 123: pydantic.SecretStr + 環境変数セキュアな設定管理

## テーマ

`pydantic.SecretStr` を使って機密情報（パスワード・APIキー・トークン）が
`repr()`・`str()`・`model_dump()` でマスクされることを検証する。
`pydantic_settings.BaseSettings` + 環境変数との組み合わせも確認する。

## 実施内容

`/home/xi/docker/nene2-python-FT/ft123-secret-settings/` に以下を実装:

- `AppConfig(BaseSettings)` — `SecretStr` フィールドで機密情報を保護
- `env_prefix = "FT123_"` で環境変数から設定を読み込む
- `ServiceConfig(BaseModel)` — リクエストボディの `SecretStr` フィールド
- `model_dump()` / `model_dump(mode="json")` での SecretStr 挙動を検証
- 9 テスト通過

## テスト結果

全 9 テスト一発通過。摩擦ゼロ。

## Friction Points

なし。

## 観察

### O1: `SecretStr` は repr/str/model_dump で自動マスクされる

```python
from pydantic import SecretStr

secret = SecretStr("my-password")

repr(secret)  # "SecretStr('**********')"
str(secret)   # "**********"
secret.get_secret_value()  # "my-password"  ← 明示的呼び出しのみ
```

structlog でエンティティを丸ごとログに出しても、`SecretStr` フィールドは `**********` になる。

### O2: `model_dump(mode="json")` でも SecretStr はマスクされる

```python
class Config(BaseModel):
    password: SecretStr

config = Config(password="my-password")
config.model_dump()             # {"password": SecretStr('**********')}  → Python オブジェクト
config.model_dump(mode="json")  # {"password": "**********"}             → マスク済み文字列
```

`JSONResponse(config.model_dump(mode="json"))` を使っても機密情報が漏れない。

### O3: `pydantic_settings` + `env_prefix` で環境変数を型安全に読み込める

```python
class AppConfig(BaseSettings):
    db_password: SecretStr = Field(default="default-secret")
    model_config = {"env_prefix": "FT123_"}

# FT123_DB_PASSWORD 環境変数が自動的に読み込まれる
config = AppConfig()
config.db_password.get_secret_value()  # 環境変数の値
```

テストでは `monkeypatch.setenv()` で環境変数を一時的に設定して検証できる。

## まとめ

FT123 は摩擦ゼロ確認。`SecretStr` + `BaseSettings` は CLAUDE.md の
「機密フィールドは `SecretStr` 型」ポリシーの正しい実装例として確認できた。
`model_dump(mode="json")` でもマスクが機能するため、JSONResponse への変換でも安全。
