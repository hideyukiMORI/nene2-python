# So führen Sie die echten Datenbankintegrationstests aus

Das Standard-`uv run pytest` läuft nur gegen SQLite / In-Memory — schnell und abhängigkeitsfrei. Eine separate Suite unter `tests/integration/` testet die Repository-Schicht gegen **echte PostgreSQL- und MySQL**-Server, die Dialekte, die das Framework zu unterstützen behauptet. Diese Tests **überspringen**, wenn die entsprechende URL-Umgebungsvariable nicht gesetzt ist, sodass sie den Standard-Lauf nie verlangsamen.

## Lokal mit Docker ausführen

Wegwerfbare Datenbanken starten:

```bash
docker run -d --name nene2-pg -e POSTGRES_PASSWORD=nene2 -e POSTGRES_DB=nene2_test \
  -p 5432:5432 postgres:16-alpine
docker run -d --name nene2-mysql -e MYSQL_ROOT_PASSWORD=nene2 -e MYSQL_DATABASE=nene2_test \
  -p 3306:3306 mysql:8
```

Die Suite auf sie zeigen und ausführen:

```bash
export NENE2_TEST_POSTGRES_URL="postgresql+psycopg2://postgres:nene2@127.0.0.1:5432/nene2_test"
export NENE2_TEST_MYSQL_URL="mysql+pymysql://root:nene2@127.0.0.1:3306/nene2_test"
uv run pytest tests/integration/ -v --no-cov
```

Setzen Sie nur eine Variable, um ein einzelnes Backend zu testen. Wenn keine gesetzt ist, wird die Suite übersprungen.

Bereinigen Sie, wenn Sie fertig sind:

```bash
docker rm -f nene2-pg nene2-mysql
```

## In CI

Der `integration-db`-Job in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) stellt PostgreSQL und MySQL als Service-Container bereit und führt diese Suite bei jedem Push und PR aus — sodass dialektspezifische Regressionen (z. B. PostgreSQLs fehlender `lastrowid`, der einst `save()` dazu brachte, den falschen Primärschlüssel zurückzugeben, #747) automatisch erkannt werden.

## Wie das Schema erstellt wird

Das Fixture erstellt das Schema aus einer SQLAlchemy-`Table`-Definition (`tests/integration/conftest.py`), sodass derselbe `Integer`-Autoincrement-Primärschlüssel auf PostgreSQL zu `SERIAL`, auf MySQL zu `AUTO_INCREMENT` und auf SQLite zu `AUTOINCREMENT` wird — kein handgeschriebenes DDL pro Dialekt. Jeder Test erhält eine frisch erstellte und gelöschte Tabelle.
