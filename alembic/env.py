"""Alembic migration environment.

Reads DB_ADAPTER / DB_NAME from environment (via AppSettings) to build
the SQLAlchemy URL. Falls back to alembic.ini sqlalchemy.url for offline mode.
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _build_url() -> str:
    """Build SQLAlchemy URL from environment variables."""
    adapter = os.getenv("DB_ADAPTER", "sqlite")
    db_name = os.getenv("DB_NAME", "data/nene2.db")

    if adapter == "sqlite":
        return f"sqlite:///{db_name}"
    if adapter == "mysql":
        user = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "3306")
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"
    if adapter == "pgsql":
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"

    return config.get_main_option("sqlalchemy.url") or ""


def run_migrations_offline() -> None:
    context.configure(
        url=_build_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    ini_section = config.get_section(config.config_ini_section, {})
    ini_section["sqlalchemy.url"] = _build_url()

    connectable = engine_from_config(
        ini_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
