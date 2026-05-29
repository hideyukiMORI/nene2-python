# Referência de configuração

Todas as configurações são gerenciadas pelo `AppSettings` (Pydantic Settings) e podem ser fornecidas via variáveis de ambiente ou um arquivo `.env`.

## Core

| Variável | Padrão | Descrição |
|---|---|---|
| `APP_ENV` | `local` | Ambiente de execução: `local` / `test` / `production` |
| `APP_DEBUG` | `false` | Incluir mensagens de exceção nas respostas 500 quando `true` |
| `APP_NAME` | `nene2-python` | Nome da aplicação |

## Segurança

| Variável | Padrão | Descrição |
|---|---|---|
| `SECURITY_HEADERS_ENABLED` | `true` | Adicionar headers de segurança a toda resposta |
| `MAX_BODY_SIZE` | `1048576` | Tamanho máximo do body da requisição em bytes (padrão 1 MiB) |

Headers de segurança adicionados quando habilitados:

| Header | Valor |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'` |
| `Permissions-Policy` | `geolocation=(), microphone=()` |

## Rate limiting

| Variável | Padrão | Descrição |
|---|---|---|
| `THROTTLE_ENABLED` | `true` | Habilitar rate limiting |
| `THROTTLE_LIMIT` | `60` | Máximo de requisições por janela |
| `THROTTLE_WINDOW` | `60` | Tamanho da janela em segundos |

Usa um algoritmo de janela fixa com chave no IP do cliente. Exceder o limite retorna `429 Too Many Requests` com um header `Retry-After`.

## CORS

| Variável | Padrão | Descrição |
|---|---|---|
| `CORS_ENABLED` | `false` | Habilitar middleware CORS |
| `CORS_ORIGINS` | `[]` | Origens permitidas (separadas por vírgula) |
| `CORS_ALLOW_CREDENTIALS` | `false` | Permitir credenciais |
| `CORS_ALLOW_METHODS` | `GET,POST,PUT,DELETE,OPTIONS` | Métodos permitidos |
| `CORS_ALLOW_HEADERS` | `*` | Headers permitidos |

> `CORS_ORIGINS=*` é **proibido**. Sempre especifique origens explícitas.

## Autenticação

| Variável | Padrão | Descrição |
|---|---|---|
| `BEARER_TOKEN_ENABLED` | `false` | Habilitar auth por Bearer Token |
| `BEARER_TOKENS` | `[]` | Tokens válidos — formato array JSON: `["tok-1","tok-2"]` |
| `API_KEY_ENABLED` | `false` | Habilitar auth por API Key |
| `API_KEYS` | `[]` | API keys válidas — formato array JSON: `["key-1","key-2"]` |

> **Campos de lista requerem sintaxe de array JSON no `.env`.**
> Escrever `BEARER_TOKENS=token-1` (string simples) causa um `JSONDecodeError` na inicialização.
> Sempre use `BEARER_TOKENS=["token-1","token-2"]`.
> O mesmo se aplica a `API_KEYS` e `CORS_ORIGINS`.

## Banco de dados

| Variável | Padrão | Descrição |
|---|---|---|
| `DB_ADAPTER` | `sqlite` | `sqlite` / `mysql` / `pgsql` |
| `DB_NAME` | `:memory:` | Caminho do arquivo SQLite ou nome do DB |
| `DB_HOST` | `localhost` | Host do banco de dados (ignorado para SQLite) |
| `DB_PORT` | `3306` | Porta do banco de dados (ignorado para SQLite) |
| `DB_USER` | `""` | Usuário do banco de dados (ignorado para SQLite) |
| `DB_PASSWORD` | `""` | Senha do banco de dados — armazenada como `SecretStr`, nunca logada |

### `db_url` gerado

`AppSettings.db_url` é uma propriedade computada construída a partir das variáveis acima.
A tabela abaixo mostra qual URL é gerada para cada adaptador + valores comuns de `DB_NAME`:

| `DB_ADAPTER` | `DB_NAME` | `db_url` gerado |
|---|---|---|
| `sqlite` | `:memory:` | `sqlite:///:memory:` |
| `sqlite` | `./data/app.db` | `sqlite:///./data/app.db` |
| `sqlite` | `/var/lib/app.db` | `sqlite:////var/lib/app.db` |
| `mysql` | `mydb` | `mysql+pymysql://user:pass@localhost:3306/mydb` |
| `pgsql` | `mydb` | `postgresql+psycopg2://user:pass@localhost:5432/mydb` |

> Para bancos SQLite em memória (`DB_NAME=:memory:`), passe `poolclass=StaticPool` para
> `create_engine()` para que todas as conexões compartilhem o mesmo banco em processo.
> Veja o [how-to do repository SQLAlchemy](../how-to/sqlalchemy-repository.md) para detalhes.

## Exemplo de `.env`

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

> Faça commit de `.env.example` com valores vazios. Mantenha o `.env` real no `.gitignore`.
