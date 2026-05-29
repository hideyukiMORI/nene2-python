# How to run the real-database integration tests

The default `uv run pytest` runs against SQLite / in-memory only — fast and
dependency-free. A separate suite under `tests/integration/` exercises the
repository layer against **real PostgreSQL and MySQL** servers, the dialects the
framework claims to support. These tests **skip** unless the corresponding URL
env var is set, so they never slow down the default run.

## Run locally with Docker

Start throwaway databases:

```bash
docker run -d --name nene2-pg -e POSTGRES_PASSWORD=nene2 -e POSTGRES_DB=nene2_test \
  -p 5432:5432 postgres:16-alpine
docker run -d --name nene2-mysql -e MYSQL_ROOT_PASSWORD=nene2 -e MYSQL_DATABASE=nene2_test \
  -p 3306:3306 mysql:8
```

Point the suite at them and run:

```bash
export NENE2_TEST_POSTGRES_URL="postgresql+psycopg2://postgres:nene2@127.0.0.1:5432/nene2_test"
export NENE2_TEST_MYSQL_URL="mysql+pymysql://root:nene2@127.0.0.1:3306/nene2_test"
uv run pytest tests/integration/ -v --no-cov
```

Set only one variable to test a single backend. With neither set, the suite is
skipped.

Tear down when finished:

```bash
docker rm -f nene2-pg nene2-mysql
```

## In CI

The `integration-db` job in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
provides PostgreSQL and MySQL as service containers and runs this suite on every
push and PR — so dialect-specific regressions (e.g. PostgreSQL's lack of
`lastrowid`, which once made `save()` return the wrong PK, #747) are caught
automatically.

## How the schema is created

The fixture builds the schema from a SQLAlchemy `Table` definition
(`tests/integration/conftest.py`), so the same `Integer` autoincrement primary
key becomes `SERIAL` on PostgreSQL, `AUTO_INCREMENT` on MySQL, and `AUTOINCREMENT`
on SQLite — no hand-written per-dialect DDL. Each test gets a freshly created and
dropped table.
