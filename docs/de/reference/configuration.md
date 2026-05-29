# Konfigurationsreferenz

Alle Einstellungen werden von `AppSettings` (Pydantic Settings) verwaltet und können über Umgebungsvariablen oder eine `.env`-Datei bereitgestellt werden.

## Kern

| Variable | Standard | Beschreibung |
|---|---|---|
| `APP_ENV` | `local` | Laufzeitumgebung: `local` / `test` / `production` |
| `APP_DEBUG` | `false` | Ausnahme-Meldungen in 500-Antworten einschließen wenn `true` |
| `APP_NAME` | `nene2-python` | Anwendungsname |

## Sicherheit

| Variable | Standard | Beschreibung |
|---|---|---|
| `SECURITY_HEADERS_ENABLED` | `true` | Sicherheitsheader zu jeder Antwort hinzufügen |
| `MAX_BODY_SIZE` | `1048576` | Maximale Request-Body-Größe in Bytes (Standard 1 MiB) |

Sicherheitsheader, die bei Aktivierung hinzugefügt werden:

| Header | Wert |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'` |
| `Permissions-Policy` | `geolocation=(), microphone=()` |

## Rate-Limiting

| Variable | Standard | Beschreibung |
|---|---|---|
| `THROTTLE_ENABLED` | `true` | Rate-Limiting aktivieren |
| `THROTTLE_LIMIT` | `60` | Maximale Anfragen pro Zeitfenster |
| `THROTTLE_WINDOW` | `60` | Zeitfenstergröße in Sekunden |

Verwendet einen Festfenster-Algorithmus mit Client-IP-Schlüssel. Das Überschreiten des Limits gibt `429 Too Many Requests` mit einem `Retry-After`-Header zurück.

## CORS

| Variable | Standard | Beschreibung |
|---|---|---|
| `CORS_ENABLED` | `false` | CORS-Middleware aktivieren |
| `CORS_ORIGINS` | `[]` | Erlaubte Origins (kommagetrennt) |
| `CORS_ALLOW_CREDENTIALS` | `false` | Credentials erlauben |
| `CORS_ALLOW_METHODS` | `GET,POST,PUT,DELETE,OPTIONS` | Erlaubte Methoden |
| `CORS_ALLOW_HEADERS` | `*` | Erlaubte Header |

> `CORS_ORIGINS=*` ist **verboten**. Geben Sie immer explizite Origins an.

## Authentifizierung

| Variable | Standard | Beschreibung |
|---|---|---|
| `BEARER_TOKEN_ENABLED` | `false` | Bearer-Token-Auth aktivieren |
| `BEARER_TOKENS` | `[]` | Gültige Tokens — JSON-Array-Format: `["tok-1","tok-2"]` |
| `API_KEY_ENABLED` | `false` | API-Key-Auth aktivieren |
| `API_KEYS` | `[]` | Gültige API-Keys — JSON-Array-Format: `["key-1","key-2"]` |

> **Listenfelder erfordern JSON-Array-Syntax in `.env`.**
> Das Schreiben von `BEARER_TOKENS=token-1` (einfacher String) verursacht beim Start einen `JSONDecodeError`. Verwenden Sie immer `BEARER_TOKENS=["token-1","token-2"]`. Dasselbe gilt für `API_KEYS` und `CORS_ORIGINS`.

## Datenbank

| Variable | Standard | Beschreibung |
|---|---|---|
| `DB_ADAPTER` | `sqlite` | `sqlite` / `mysql` / `pgsql` |
| `DB_NAME` | `:memory:` | SQLite-Dateipfad oder DB-Name |
| `DB_HOST` | `localhost` | Datenbank-Host (für SQLite ignoriert) |
| `DB_PORT` | `3306` | Datenbank-Port (für SQLite ignoriert) |
| `DB_USER` | `""` | Datenbankbenutzer (für SQLite ignoriert) |
| `DB_PASSWORD` | `""` | Datenbankkennwort — als `SecretStr` gespeichert, nie geloggt |

### Generierte `db_url`

`AppSettings.db_url` ist eine berechnete Eigenschaft, die aus den obigen Variablen aufgebaut wird. Die folgende Tabelle zeigt, welche URL für jeden Adapter + gängige `DB_NAME`-Werte generiert wird:

| `DB_ADAPTER` | `DB_NAME` | Generierte `db_url` |
|---|---|---|
| `sqlite` | `:memory:` | `sqlite:///:memory:` |
| `sqlite` | `./data/app.db` | `sqlite:///./data/app.db` |
| `sqlite` | `/var/lib/app.db` | `sqlite:////var/lib/app.db` |
| `mysql` | `mydb` | `mysql+pymysql://user:pass@localhost:3306/mydb` |
| `pgsql` | `mydb` | `postgresql+psycopg2://user:pass@localhost:5432/mydb` |

> Für SQLite-In-Memory-Datenbanken (`DB_NAME=:memory:`) übergeben Sie `poolclass=StaticPool` an `create_engine()`, damit alle Verbindungen dieselbe In-Process-Datenbank teilen. Einzelheiten finden Sie im [SQLAlchemy-Repository How-to](../how-to/sqlalchemy-repository.md).

## Beispiel `.env`

```dotenv
APP_ENV=production
APP_DEBUG=false

THROTTLE_ENABLED=true
THROTTLE_LIMIT=100
THROTTLE_WINDOW=60

CORS_ENABLED=true
CORS_ORIGINS=["https://example.com","https://app.example.com"]

BEARER_TOKEN_ENABLED=true
BEARER_TOKENS=["secret-token-1","secret-token-2"]

DB_ADAPTER=mysql
DB_HOST=db.example.com
DB_PORT=3306
DB_NAME=myapp
DB_USER=myuser
DB_PASSWORD=supersecret
```

> Committen Sie `.env.example` mit leeren Werten. Halten Sie die echte `.env` in `.gitignore`.
