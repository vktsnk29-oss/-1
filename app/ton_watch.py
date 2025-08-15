# app/ton_watch.py
from __future__ import annotations

import asyncio
from typing import Optional, Tuple

import httpx

from . import db  # модуль с engine/init_db
from .config import load_settings

settings = load_settings()


def _base_url() -> str:
    # нормализуем базовый URL toncenter
    url = str(settings.ton_api_base)
    return url.rstrip("/") + "/"


async def _get_transactions(address: str, limit: int = 16, to_lt: Optional[str] = None) -> dict:
    headers = {}
    params = {"address": address, "limit": limit}

    if settings.ton_api_key:
        # ключ одновременно в хедере и в query — максимально совместимо
        headers["X-API-Key"] = settings.ton_api_key
        params["api_key"] = settings.ton_api_key

    if to_lt:
        params["to_lt"] = to_lt

    async with httpx.AsyncClient(base_url=_base_url(), headers=headers, timeout=15) as client:
        r = await client.get("getTransactions", params=params)
        r.raise_for_status()
        return r.json()


def _ensure_state_table() -> None:
    """
    Минимальная схема для хранения курсора: таблица state(key, value, updated_at).
    """
    if db.engine is None:
        db.init_db(settings.database_url)

    with db.engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS state (
                key VARCHAR(64) PRIMARY KEY,
                value VARCHAR(256) NOT NULL,
                updated_at TIMESTAMPTZ
            )
            """
        )
        conn.exec_driver_sql(
            "ALTER TABLE state ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ"
        )


def _get_state(key: str) -> Optional[str]:
    if db.engine is None:
        db.init_db(settings.database_url)
    with db.engine.begin() as conn:
        row = conn.exec_driver_sql(
            "SELECT value FROM state WHERE key = %(k)s::VARCHAR",
            {"k": key},
        ).first()
        return row[0] if row else None


def _set_state(key: str, value: str) -> None:
    if db.engine is None:
        db.init_db(settings.database_url)
    with db.engine.begin() as conn:
        conn.exec_driver_sql(
            """
            INSERT INTO state (key, value, updated_at)
            VALUES (%(k)s, %(v)s, NOW())
            ON CONFLICT (key) DO UPDATE
            SET value = excluded.value,
                updated_at = NOW()
            """,
            {"k": key, "v": value},
        )


def _extract_max_lt(payload: dict) -> Optional[str]:
    """
    Toncenter возвращает список транзакций. Берём максимальный lt из transaction_id.
    """
    try:
        txs = payload.get("result") or payload.get("transactions") or []
        lts = []
        for tx in txs:
            # разные ответы у разных провайдеров, но у toncenter есть "transaction_id": {"lt": "..."}
            tid = tx.get("transaction_id") or {}
            lt = tid.get("lt")
            if lt:
                lts.append(int(lt))
        if not lts:
            return None
        return str(max(lts))
    except Exception:
        return None


async def poll_once() -> None:
    """
    Один проход: читаем курсор, запрашиваем новые транзакции, двигаем курсор.
    """
    _ensure_state_table()

    to_lt = _get_state("ton_last_lt")
    data = await _get_transactions(settings.ton_address, limit=16, to_lt=to_lt)

    max_lt = _extract_max_lt(data)
    if max_lt and max_lt != to_lt:
        _set_state("ton_last_lt", max_lt)

    # здесь могла бы быть логика разборки входящих платежей и зачёта депозитов
    # (сопоставление по комментарию `tag`), но для текущей задачи важно,
    # чтобы watcher стабильно работал и не падал по 401/схеме БД.


async def run_watcher() -> None:
    """
    Фоновый вочер: крутится каждые N секунд, ошибки логируем и продолжаем.
    """
    interval = int(settings.ton_poll_interval or 5)
    while True:
        try:
            await poll_once()
        except Exception as e:
            print("ton_watcher_error")
            import traceback

            traceback.print_exc()
        await asyncio.sleep(interval)
