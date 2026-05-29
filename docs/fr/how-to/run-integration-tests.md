# Comment exécuter les tests d'intégration sur une vraie base de données

`uv run pytest` par défaut s'exécute uniquement contre SQLite / en mémoire — rapide et sans
dépendances. Une suite séparée dans `tests/integration/` teste la couche repository contre de
**vrais serveurs PostgreSQL et MySQL**, les dialectes que le framework prétend supporter. Ces
tests se **sautent** automatiquement sauf si la variable d'environnement URL correspondante est
définie, donc ils ne ralentissent jamais l'exécution par défaut.

## Exécuter localement avec Docker

Démarrer des bases de données temporaires :

```bash
docker run -d --name nene2-pg -e POSTGRES_PASSWORD=nene2 -e POSTGRES_DB=nene2_test \
  -p 5432:5432 postgres:16-alpine
docker run -d --name nene2-mysql -e MYSQL_ROOT_PASSWORD=nene2 -e MYSQL_DATABASE=nene2_test \
  -p 3306:3306 mysql:8
```

Pointer la suite dessus et l'exécuter :

```bash
export NENE2_TEST_POSTGRES_URL="postgresql+psycopg2://postgres:nene2@127.0.0.1:5432/nene2_test"
export NENE2_TEST_MYSQL_URL="mysql+pymysql://root:nene2@127.0.0.1:3306/nene2_test"
uv run pytest tests/integration/ -v --no-cov
```

Définir seulement une variable pour tester un seul backend. Sans aucune variable définie, la
suite est ignorée.

Nettoyer à la fin :

```bash
docker rm -f nene2-pg nene2-mysql
```

## En CI

Le job `integration-db` dans [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
fournit PostgreSQL et MySQL comme conteneurs de service et exécute cette suite à chaque push
et PR — ainsi les régressions spécifiques aux dialectes (p. ex. l'absence de `lastrowid` dans
PostgreSQL, qui avait fait retourner la mauvaise PK à `save()`, #747) sont détectées automatiquement.

## Comment le schéma est créé

La fixture construit le schéma à partir d'une définition `Table` SQLAlchemy
(`tests/integration/conftest.py`), de sorte que la même clé primaire entière autoincrement
devient `SERIAL` sur PostgreSQL, `AUTO_INCREMENT` sur MySQL, et `AUTOINCREMENT` sur SQLite —
sans DDL manuel par dialecte. Chaque test obtient une table fraîchement créée et supprimée.
