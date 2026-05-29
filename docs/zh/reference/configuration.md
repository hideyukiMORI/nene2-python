# 配置参考

所有设置均通过 `AppSettings`（Pydantic Settings）管理，可通过环境变量或 `.env` 文件提供。

## 核心配置

| 变量 | 默认值 | 描述 |
|---|---|---|
| `APP_ENV` | `local` | 运行环境：`local` / `test` / `production` |
| `APP_DEBUG` | `false` | 为 `true` 时在 500 响应中包含异常消息 |
| `APP_NAME` | `nene2-python` | 应用名称 |

## 安全

| 变量 | 默认值 | 描述 |
|---|---|---|
| `SECURITY_HEADERS_ENABLED` | `true` | 在每个响应中添加安全头 |
| `MAX_BODY_SIZE` | `1048576` | 最大请求体大小（字节，默认 1 MiB） |

启用时添加的安全头：

| 头部 | 值 |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'` |
| `Permissions-Policy` | `geolocation=(), microphone=()` |

## 限流

| 变量 | 默认值 | 描述 |
|---|---|---|
| `THROTTLE_ENABLED` | `true` | 启用限流 |
| `THROTTLE_LIMIT` | `60` | 每窗口最大请求数 |
| `THROTTLE_WINDOW` | `60` | 窗口大小（秒） |

使用基于客户端 IP 的固定窗口算法。超过限制时返回 `429 Too Many Requests` 并附带 `Retry-After` 头。

## CORS

| 变量 | 默认值 | 描述 |
|---|---|---|
| `CORS_ENABLED` | `false` | 启用 CORS middleware |
| `CORS_ORIGINS` | `[]` | 允许的来源（逗号分隔） |
| `CORS_ALLOW_CREDENTIALS` | `false` | 允许凭据 |
| `CORS_ALLOW_METHODS` | `GET,POST,PUT,DELETE,OPTIONS` | 允许的方法 |
| `CORS_ALLOW_HEADERS` | `*` | 允许的头部 |

> **禁止使用 `CORS_ORIGINS=*`。** 请始终指定明确的来源。

## 身份验证

| 变量 | 默认值 | 描述 |
|---|---|---|
| `BEARER_TOKEN_ENABLED` | `false` | 启用 Bearer Token 认证 |
| `BEARER_TOKENS` | `[]` | 有效 Token — JSON 数组格式：`["tok-1","tok-2"]` |
| `API_KEY_ENABLED` | `false` | 启用 API Key 认证 |
| `API_KEYS` | `[]` | 有效 API Key — JSON 数组格式：`["key-1","key-2"]` |

> **列表字段在 `.env` 中需要 JSON 数组语法。**
> 写成 `BEARER_TOKENS=token-1`（纯字符串）会在启动时导致 `JSONDecodeError`。
> 请始终使用 `BEARER_TOKENS=["token-1","token-2"]`。
> `API_KEYS` 和 `CORS_ORIGINS` 同理。

## 数据库

| 变量 | 默认值 | 描述 |
|---|---|---|
| `DB_ADAPTER` | `sqlite` | `sqlite` / `mysql` / `pgsql` |
| `DB_NAME` | `:memory:` | SQLite 文件路径或数据库名称 |
| `DB_HOST` | `localhost` | 数据库主机（SQLite 时忽略） |
| `DB_PORT` | `3306` | 数据库端口（SQLite 时忽略） |
| `DB_USER` | `""` | 数据库用户（SQLite 时忽略） |
| `DB_PASSWORD` | `""` | 数据库密码 — 存储为 `SecretStr`，不会写入日志 |

### 生成的 `db_url`

`AppSettings.db_url` 是根据上述变量计算出的属性。下表展示了各适配器和常用 `DB_NAME` 值生成的 URL：

| `DB_ADAPTER` | `DB_NAME` | 生成的 `db_url` |
|---|---|---|
| `sqlite` | `:memory:` | `sqlite:///:memory:` |
| `sqlite` | `./data/app.db` | `sqlite:///./data/app.db` |
| `sqlite` | `/var/lib/app.db` | `sqlite:////var/lib/app.db` |
| `mysql` | `mydb` | `mysql+pymysql://user:pass@localhost:3306/mydb` |
| `pgsql` | `mydb` | `postgresql+psycopg2://user:pass@localhost:5432/mydb` |

> 对于内存 SQLite（`DB_NAME=:memory:`），向 `create_engine()` 传入 `poolclass=StaticPool`，确保所有连接共享同一个内存数据库。详见 [SQLAlchemy repository 操作指南](../how-to/sqlalchemy-repository.md)。

## `.env` 示例

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

> 提交含空值的 `.env.example`，将真实 `.env` 加入 `.gitignore`。
