# 設定リファレンス（環境変数）

設定は `pydantic-settings` で管理されており、環境変数または `.env` ファイルから読み込みます。

## 基本設定

| 変数 | デフォルト | 説明 |
|---|---|---|
| `APP_ENV` | `local` | 実行環境。`local` / `test` / `production` |
| `APP_DEBUG` | `false` | `true` の場合、500 エラーに例外メッセージを含める |
| `APP_NAME` | `nene2-python` | アプリケーション名 |

## セキュリティ設定

| 変数 | デフォルト | 説明 |
|---|---|---|
| `SECURITY_HEADERS_ENABLED` | `true` | セキュリティヘッダー付与を有効化 |
| `MAX_BODY_SIZE` | `1048576` | リクエストボディの最大バイト数（デフォルト 1 MiB） |

セキュリティヘッダーの内容:

| ヘッダー | 値 |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'` |
| `Permissions-Policy` | `geolocation=(), microphone=()` |

## レートリミット

| 変数 | デフォルト | 説明 |
|---|---|---|
| `THROTTLE_ENABLED` | `true` | レートリミットを有効化 |
| `THROTTLE_LIMIT` | `60` | ウィンドウ内の最大リクエスト数 |
| `THROTTLE_WINDOW` | `60` | ウィンドウの秒数 |

固定ウィンドウ方式（IP アドレスをキーとする）。制限超過時は `429 Too Many Requests` + `Retry-After` ヘッダー。

## CORS 設定

| 変数 | デフォルト | 説明 |
|---|---|---|
| `CORS_ENABLED` | `false` | CORS ミドルウェアを有効化 |
| `CORS_ORIGINS` | `[]` | 許可オリジンのリスト（カンマ区切り） |
| `CORS_ALLOW_CREDENTIALS` | `false` | クレデンシャルを許可するか |
| `CORS_ALLOW_METHODS` | `GET,POST,PUT,DELETE,OPTIONS` | 許可メソッド |
| `CORS_ALLOW_HEADERS` | `*` | 許可ヘッダー |

> `CORS_ORIGINS=*` は禁止です。許可オリジンを明示してください。

## 認証設定

| 変数 | デフォルト | 説明 |
|---|---|---|
| `BEARER_TOKEN_ENABLED` | `false` | Bearer Token 認証を有効化 |
| `BEARER_TOKENS` | `[]` | 有効なトークンのリスト（カンマ区切り） |
| `API_KEY_ENABLED` | `false` | API Key 認証を有効化 |
| `API_KEYS` | `[]` | 有効な API キーのリスト（カンマ区切り） |

## データベース設定

| 変数 | デフォルト | 説明 |
|---|---|---|
| `DB_ADAPTER` | `sqlite` | `sqlite` / `mysql` / `pgsql` |
| `DB_NAME` | `:memory:` | SQLite のファイルパスまたは DB 名 |
| `DB_HOST` | `localhost` | DB ホスト（SQLite では無視） |
| `DB_PORT` | `3306` | DB ポート（SQLite では無視） |
| `DB_USER` | `""` | DB ユーザー名（SQLite では無視） |
| `DB_PASSWORD` | `""` | DB パスワード — `SecretStr` 型（ログに出力されない） |

### 接続 URL の例

| アダプター | 生成される URL |
|---|---|
| `sqlite` | `sqlite:///path/to/db.sqlite3` |
| `mysql` | `mysql+pymysql://user:pass@host:3306/dbname` |
| `pgsql` | `postgresql+psycopg2://user:pass@host:5432/dbname` |

## .env ファイル例

```dotenv
APP_ENV=production
APP_DEBUG=false
APP_NAME=my-api

THROTTLE_ENABLED=true
THROTTLE_LIMIT=100
THROTTLE_WINDOW=60

CORS_ENABLED=true
CORS_ORIGINS=https://example.com,https://app.example.com

BEARER_TOKEN_ENABLED=true
BEARER_TOKENS=secret-token-1,secret-token-2

DB_ADAPTER=mysql
DB_HOST=db.example.com
DB_PORT=3306
DB_NAME=myapp
DB_USER=myuser
DB_PASSWORD=supersecret
```

> `.env` ファイルは `.gitignore` で除外してください。`.env.example` にキー一覧をコミットしてください。
