# 如何运行真实数据库集成测试

默认的 `uv run pytest` 仅针对 SQLite / 内存数据库运行，速度快且无依赖。`tests/integration/` 下有一套独立的测试套件，针对**真实的 PostgreSQL 和 MySQL** 服务器测试 repository 层，即框架声称支持的方言。这些测试在未设置对应 URL 环境变量时会**自动跳过**，不会影响默认运行的速度。

## 使用 Docker 在本地运行

启动临时数据库：

```bash
docker run -d --name nene2-pg -e POSTGRES_PASSWORD=nene2 -e POSTGRES_DB=nene2_test \
  -p 5432:5432 postgres:16-alpine
docker run -d --name nene2-mysql -e MYSQL_ROOT_PASSWORD=nene2 -e MYSQL_DATABASE=nene2_test \
  -p 3306:3306 mysql:8
```

指向数据库并运行：

```bash
export NENE2_TEST_POSTGRES_URL="postgresql+psycopg2://postgres:nene2@127.0.0.1:5432/nene2_test"
export NENE2_TEST_MYSQL_URL="mysql+pymysql://root:nene2@127.0.0.1:3306/nene2_test"
uv run pytest tests/integration/ -v --no-cov
```

只设置一个变量即可单独测试某个后端。两者都不设置时，测试套件会被跳过。

完成后清理：

```bash
docker rm -f nene2-pg nene2-mysql
```

## 在 CI 中

[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) 中的 `integration-db` job 提供 PostgreSQL 和 MySQL 作为服务容器，并在每次推送和 PR 时运行此测试套件 — 这样就能自动捕获方言特有的回归问题（例如 PostgreSQL 缺少 `lastrowid` 导致 `save()` 返回错误主键的问题，#747）。

## schema 的创建方式

fixture 通过 SQLAlchemy 的 `Table` 定义（`tests/integration/conftest.py`）来构建 schema，相同的 `Integer` 自增主键在 PostgreSQL 上变为 `SERIAL`，在 MySQL 上变为 `AUTO_INCREMENT`，在 SQLite 上变为 `AUTOINCREMENT` — 无需手写各方言的 DDL。每个测试都会获得全新创建和删除的表。
