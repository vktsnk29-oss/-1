# migrations/env.py
from __future__ import annotations

import os
import sys
from alembic import context
from sqlalchemy import engine_from_config, pool

# добавить корень проекта, чтобы импортировать app.*
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import Base  # noqa: E402
from app import models  # noqa: F401,E402

config = context.config

def _normalize(url: str) -> str:
    # postgres:// -> postgresql:// ; добавить драйвер psycopg (v3)
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+psycopg" not in url and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

# Берём URL ТОЛЬКО из переменной окружения. Если её нет — падаем с понятной ошибкой.
env_url = os.getenv("DATABASE_URL")
if not env_url:
    raise RuntimeError(
        "DATABASE_URL is not set. Set it in Render Environment. "
        "Alembic on Render reads DB URL from ENV, not from alembic.ini."
    )

config.set_main_option("sqlalchemy.url", _normalize(env_url))

target_metadata = Base.metadata

def run_migrations_offline() -> None:
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
    section = config.get_section(config.config_ini_section) or {}
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
