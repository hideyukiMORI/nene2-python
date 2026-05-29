# Como executar os testes de integração com banco de dados real

O `uv run pytest` padrão executa contra SQLite / em memória apenas — rápido e
sem dependências. Uma suite separada em `tests/integration/` exercita a camada de
repository contra servidores **reais de PostgreSQL e MySQL**, os dialetos que o
framework afirma suportar. Esses testes **são pulados** a menos que a variável de
ambiente de URL correspondente esteja definida, então nunca atrasam a execução padrão.

## Executar localmente com Docker

Inicie bancos de dados descartáveis:

```bash
docker run -d --name nene2-pg -e POSTGRES_PASSWORD=nene2 -e POSTGRES_DB=nene2_test \
  -p 5432:5432 postgres:16-alpine
docker run -d --name nene2-mysql -e MYSQL_ROOT_PASSWORD=nene2 -e MYSQL_DATABASE=nene2_test \
  -p 3306:3306 mysql:8
```

Aponte a suite para eles e execute:

```bash
export NENE2_TEST_POSTGRES_URL="postgresql+psycopg2://postgres:nene2@127.0.0.1:5432/nene2_test"
export NENE2_TEST_MYSQL_URL="mysql+pymysql://root:nene2@127.0.0.1:3306/nene2_test"
uv run pytest tests/integration/ -v --no-cov
```

Defina apenas uma variável para testar um único backend. Com nenhuma definida, a suite é
pulada.

Encerre quando terminar:

```bash
docker rm -f nene2-pg nene2-mysql
```

## Na CI

O job `integration-db` em [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
fornece PostgreSQL e MySQL como containers de serviço e executa esta suite em todo
push e PR — para que regressões específicas de dialeto (ex: a falta de
`lastrowid` no PostgreSQL, que uma vez fez `save()` retornar o PK errado, #747) sejam
capturadas automaticamente.

## Como o schema é criado

O fixture constrói o schema a partir de uma definição `Table` do SQLAlchemy
(`tests/integration/conftest.py`), então o mesmo `Integer` autoincrement primary
key se torna `SERIAL` no PostgreSQL, `AUTO_INCREMENT` no MySQL e `AUTOINCREMENT`
no SQLite — sem DDL escrito à mão por dialeto. Cada teste recebe uma tabela
criada e dropada de forma limpa.
