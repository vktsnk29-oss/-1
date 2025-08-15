# app/web.py
from __future__ import annotations

import asyncio
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import ApplicationBuilder
from sqlalchemy import text  # на будущее, если понадобится

from .config import load_settings
from . import db  # ВАЖНО: импортируем модуль, а не переменные!
from .handlers import register as register_handlers

# Загружаем конфиг и инициализируем БД
settings = load_settings()
db.init_db(settings.database_url)

app = FastAPI(title="Telegram Bot Webhook")

# Telegram application
tg_app = ApplicationBuilder().token(settings.bot_token.get_secret_value()).build()
register_handlers(tg_app)

# Опциональный TON watcher
_watcher_task = None
try:
    from .ton_watch import run_watcher  # noqa
except Exception:
    run_watcher = None  # type: ignore


def ensure_schema() -> None:
    """
    Создаём отсутствующие элементы схемы без Alembic.
    - Таблица state (если нет)
    - Колонка state.updated_at (если нет)
    """
    try:
        if db.engine is None:
            # если по какой-то причине не инициализировалось — повторим
            db.init_db(settings.database_url)
        with db.engine.begin() as conn:
            conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS state (
                    key VARCHAR(64) PRIMARY KEY,
                    value VARCHAR(256) NOT NULL
                )
            """)
            conn.exec_driver_sql("""
                ALTER TABLE state
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ
            """)
            conn.exec_driver_sql("""
                UPDATE state
                SET updated_at = NOW()
                WHERE updated_at IS NULL
            """)
    except Exception as e:
        print("ensure_schema_error", e)


@app.on_event("startup")
async def on_startup():
    # 0) Чиним схему БД до любых SELECT
    ensure_schema()

    # 1) Telegram App
    await tg_app.initialize()
    await tg_app.start()

    # 2) Ставим корректный вебхук (без двойного слэша)
    url = str(settings.base_url).rstrip("/") + settings.webhook_path
    await tg_app.bot.set_webhook(url, secret_token=settings.telegram_webhook_secret)

    # 3) Запускаем фонового вочера TON (если есть)
    global _watcher_task
    if run_watcher:
        _watcher_task = asyncio.create_task(run_watcher())


@app.on_event("shutdown")
async def on_shutdown():
    if _watcher_task:
        _watcher_task.cancel()
    await tg_app.stop()
    await tg_app.shutdown()


@app.post(settings.webhook_path)
async def telegram_webhook(request: Request):
    # Проверяем секретный заголовок Telegram
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not secret or secret != settings.telegram_webhook_secret:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return JSONResponse({"ok": True})


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
