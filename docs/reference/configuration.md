# Configuration reference

All settings are managed by `AppSettings` (Pydantic Settings) and can be provided via environment variables or a `.env` file.

## Core

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `local` | Runtime environment: `local` / `test` / `production` |
| `APP_DEBUG` | `false` | Include exception messages in 500 responses when `true` |
| `APP_NAME` | `nene2-python` | Application name |

## Security

| Variable | Default | Description |
|---|---|---|
| `SECURITY_HEADERS_ENABLED` | `true` | Add security headers to every response |
| `MAX_BODY_SIZE` | `1048576` | Maximum request body size in bytes (default 1 MiB) |

Security headers added when enabled:

| Header | Value |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'` |
| `Permissions-Policy` | `geolocation=(), microphone=()` |

## Rate limiting

| Variable | Default | Description |
|---|---|---|
| `THROTTLE_ENABLED` | `true` | Enable rate limiting |
| `THROTTLE_LIMIT` | `60` | Maximum requests per window |
| `THROTTLE_WINDOW` | `60` | Window size in seconds |

Uses a fixed-window algorithm keyed on client IP. Exceeding the limit returns `429 Too Many Requests` with a `Retry-After` header.

## CORS

| Variable | Default | Description |
|---|---|---|
| `CORS_ENABLED` | `false` | Enable CORS middleware |
| `CORS_ORIGINS` | `[]` | Allowed origins (comma-separated) |
| `CORS_ALLOW_CREDENTIALS` | `false` | Allow credentials |
| `CORS_ALLOW_METHODS` | `GET,POST,PUT,DELETE,OPTIONS` | Allowed methods |
| `CORS_ALLOW_HEADERS` | `*` | Allowed headers |

> `CORS_ORIGINS=*` is **prohibited**. Always specify explicit origins.

## Authentication

| Variable | Default | Description |
|---|---|---|
| `BEARER_TOKEN_ENABLED` | `false` | Enable Bearer Token auth |
| `BEARER_TOKENS` | `[]` | Valid tokens (comma-separated) |
| `API_KEY_ENABLED` | `false` | Enable API Key auth |
| `API_KEYS` | `[]` | Valid API keys (comma-separated) |

## Database

| Variable | Default | Description |
|---|---|---|
| `DB_ADAPTER` | `sqlite` | `sqlite` / `mysql` / `pgsql` |
| `DB_NAME` | `:memory:` | SQLite file path or DB name |
| `DB_HOST` | `localhost` | Database host (ignored for SQLite) |
| `DB_PORT` | `3306` | Database port (ignored for SQLite) |
| `DB_USER` | `""` | Database user (ignored for SQLite) |
| `DB_PASSWORD` | `""` | Database password — stored as `SecretStr`, never logged |

### Generated connection URLs

| Adapter | URL format |
|---|---|
| `sqlite` | `sqlite:///path/to/db.sqlite3` |
| `mysql` | `mysql+pymysql://user:pass@host:3306/dbname` |
| `pgsql` | `postgresql+psycopg2://user:pass@host:5432/dbname` |

## Example `.env`

```dotenv
APP_ENV=production
APP_DEBUG=false

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

> Commit `.env.example` with empty values. Keep the real `.env` in `.gitignore`.
