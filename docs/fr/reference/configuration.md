# Référence de configuration

Tous les paramètres sont gérés par `AppSettings` (Pydantic Settings) et peuvent être fournis
via des variables d'environnement ou un fichier `.env`.

## Noyau

| Variable | Défaut | Description |
|---|---|---|
| `APP_ENV` | `local` | Environnement d'exécution : `local` / `test` / `production` |
| `APP_DEBUG` | `false` | Inclure les messages d'exception dans les réponses 500 quand `true` |
| `APP_NAME` | `nene2-python` | Nom de l'application |

## Sécurité

| Variable | Défaut | Description |
|---|---|---|
| `SECURITY_HEADERS_ENABLED` | `true` | Ajouter les en-têtes de sécurité à chaque réponse |
| `MAX_BODY_SIZE` | `1048576` | Taille maximale du corps de requête en octets (défaut 1 Mio) |

En-têtes de sécurité ajoutés quand activés :

| En-tête | Valeur |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'` |
| `Permissions-Policy` | `geolocation=(), microphone=()` |

## Limitation de débit

| Variable | Défaut | Description |
|---|---|---|
| `THROTTLE_ENABLED` | `true` | Activer la limitation de débit |
| `THROTTLE_LIMIT` | `60` | Requêtes maximales par fenêtre |
| `THROTTLE_WINDOW` | `60` | Taille de la fenêtre en secondes |

Utilise un algorithme à fenêtre fixe indexé sur l'IP du client. Dépasser la limite retourne
`429 Too Many Requests` avec un en-tête `Retry-After`.

## CORS

| Variable | Défaut | Description |
|---|---|---|
| `CORS_ENABLED` | `false` | Activer le middleware CORS |
| `CORS_ORIGINS` | `[]` | Origines autorisées (séparées par des virgules) |
| `CORS_ALLOW_CREDENTIALS` | `false` | Autoriser les credentials |
| `CORS_ALLOW_METHODS` | `GET,POST,PUT,DELETE,OPTIONS` | Méthodes autorisées |
| `CORS_ALLOW_HEADERS` | `*` | En-têtes autorisés |

> `CORS_ORIGINS=*` est **interdit**. Spécifiez toujours des origines explicites.

## Authentification

| Variable | Défaut | Description |
|---|---|---|
| `BEARER_TOKEN_ENABLED` | `false` | Activer l'auth par Bearer Token |
| `BEARER_TOKENS` | `[]` | Tokens valides — format tableau JSON : `["tok-1","tok-2"]` |
| `API_KEY_ENABLED` | `false` | Activer l'auth par clé API |
| `API_KEYS` | `[]` | Clés API valides — format tableau JSON : `["key-1","key-2"]` |

> **Les champs de liste nécessitent la syntaxe de tableau JSON dans `.env`.**
> Écrire `BEARER_TOKENS=token-1` (chaîne brute) provoque un `JSONDecodeError` au démarrage.
> Utilisez toujours `BEARER_TOKENS=["token-1","token-2"]`.
> La même règle s'applique à `API_KEYS` et `CORS_ORIGINS`.

## Base de données

| Variable | Défaut | Description |
|---|---|---|
| `DB_ADAPTER` | `sqlite` | `sqlite` / `mysql` / `pgsql` |
| `DB_NAME` | `:memory:` | Chemin du fichier SQLite ou nom de la DB |
| `DB_HOST` | `localhost` | Hôte de la base de données (ignoré pour SQLite) |
| `DB_PORT` | `3306` | Port de la base de données (ignoré pour SQLite) |
| `DB_USER` | `""` | Utilisateur de la base de données (ignoré pour SQLite) |
| `DB_PASSWORD` | `""` | Mot de passe de la base de données — stocké comme `SecretStr`, jamais journalisé |

### `db_url` généré

`AppSettings.db_url` est une propriété calculée construite à partir des variables ci-dessus.
Le tableau ci-dessous montre quelle URL est générée pour chaque adaptateur + valeurs communes de `DB_NAME` :

| `DB_ADAPTER` | `DB_NAME` | `db_url` généré |
|---|---|---|
| `sqlite` | `:memory:` | `sqlite:///:memory:` |
| `sqlite` | `./data/app.db` | `sqlite:///./data/app.db` |
| `sqlite` | `/var/lib/app.db` | `sqlite:////var/lib/app.db` |
| `mysql` | `mydb` | `mysql+pymysql://user:pass@localhost:3306/mydb` |
| `pgsql` | `mydb` | `postgresql+psycopg2://user:pass@localhost:5432/mydb` |

> Pour les bases SQLite en mémoire (`DB_NAME=:memory:`), passez `poolclass=StaticPool` à
> `create_engine()` pour que toutes les connexions partagent la même base de données en
> processus. Voir le [guide how-to SQLAlchemy repository](../how-to/sqlalchemy-repository.md)
> pour les détails.

## Exemple `.env`

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

> Commitez `.env.example` avec des valeurs vides. Gardez le vrai `.env` dans `.gitignore`.
