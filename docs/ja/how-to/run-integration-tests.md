# 実データベース統合テストの実行方法

デフォルトの `uv run pytest` は SQLite / インメモリのみを対象とし、高速で外部依存が
ない。`tests/integration/` 配下の別スイートは、フレームワークが対応を謳う方言である
**実 PostgreSQL / MySQL** に対してリポジトリ層を検証する。これらは対応する URL の
環境変数が設定されている時だけ実行され、未設定なら**スキップ**される — デフォルトの
実行を遅くしない。

## Docker でローカル実行

捨てDBを起動:

```bash
docker run -d --name nene2-pg -e POSTGRES_PASSWORD=nene2 -e POSTGRES_DB=nene2_test \
  -p 5432:5432 postgres:16-alpine
docker run -d --name nene2-mysql -e MYSQL_ROOT_PASSWORD=nene2 -e MYSQL_DATABASE=nene2_test \
  -p 3306:3306 mysql:8
```

スイートを向けて実行:

```bash
export NENE2_TEST_POSTGRES_URL="postgresql+psycopg2://postgres:nene2@127.0.0.1:5432/nene2_test"
export NENE2_TEST_MYSQL_URL="mysql+pymysql://root:nene2@127.0.0.1:3306/nene2_test"
uv run pytest tests/integration/ -v --no-cov
```

片方だけ設定すれば単一バックエンドのみ検証。どちらも未設定ならスキップ。

後始末:

```bash
docker rm -f nene2-pg nene2-mysql
```

## CI での実行

[`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml) の `integration-db`
ジョブが PostgreSQL / MySQL を service container として提供し、push / PR ごとに本
スイートを実行する。これにより方言固有のリグレッション（例: PostgreSQL は `lastrowid`
を持たず、かつて `save()` が誤ったPKを返していた #747）が自動で検出される。

## スキーマの作り方

フィクスチャは SQLAlchemy の `Table` 定義（`tests/integration/conftest.py`）から
スキーマを生成するため、同じ `Integer` autoincrement 主キーが PostgreSQL では
`SERIAL`、MySQL では `AUTO_INCREMENT`、SQLite では `AUTOINCREMENT` になる — 方言別の
手書きDDLは不要。各テストはテーブルを作成→破棄したクリーンな状態で走る。
