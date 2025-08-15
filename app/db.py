# app/db.py
from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

engine = None
SessionLocal = None
Base = declarative_base()

def _normalize_db_url(url: str) -> str:
    # render/managed DB иногда дают postgres:// — нормализуем
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    # если драйвер не указан — используем psycopg (v3)
    if url.startswith("postgresql://") and "+psycopg" not in url and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

def init_db(database_url: str):
    global engine, SessionLocal
    database_url = _normalize_db_url(database_url)
    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
