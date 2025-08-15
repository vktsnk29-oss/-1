# migrations/env.py
from __future__ import annotations

import os
import sys
from alembic import context
from sqlalchemy import engine_from_config, pool

# Добавляем корень проекта в PYTHONPATH, чтобы найти app.*
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import Base  # noqa: E402
from app import models  # noqa: F401,E402  # важно импортнуть модели, чтобы metadata была заполнена

# Это объект Alembic Config, предоставляет доступ к значениям из .ini
config = context.config

# Позволим задавать URL БД через ENV (Render передаёт DATABASE_URL)
if os.getenv("DATABASE_URL"):
    config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# Метадата для автогенерации
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск в офлайн-режиме (без подключения)."""
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
    """Запуск в онлайн-режиме (с подключением к БД)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
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
