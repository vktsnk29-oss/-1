# migrations/env.py
from __future__ import annotations

import os
import sys
from alembic import context
from sqlalchemy import engine_from_config, pool

# Добавляем корень проекта в PYTHONPATH, чтобы импортировать app.*
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import Base  # noqa: E402
from app import models  # noqa: F401,E402  # важно импортнуть модели, чтобы metadata была заполнена

# Alembic config
config = context.config


def _normalized_db_url(raw: str | None) -> str | None:
    """Нормализуем URL: postgres:// -> postgresql:// и добавляем драйвер psycopg (v3)."""
    if not raw:
        return raw
    url = raw
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+psycopg" not in url and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


# Берём URL из ENV либо из alembic.ini
_env_url = _normalized_db_url(os.getenv("DATABASE_URL"))
_ini_url = _normalized_db_url(config.get_main_option("sqlalchemy.url"))
final_url = _env_url or _ini_url
if final_url:
    config.set_main_option("sqlalchemy.url", final_url)

# Метадата для автогенерации
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск миграций без подключения к БД."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запуск миграций с подключением к БД."""
    section = config.get_section(config.config_ini_section) or {}
    # engine_from_config читает sqlalchemy.url из config, мы его уже проставили выше
    connectable = engine_from_config(
        section,
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
