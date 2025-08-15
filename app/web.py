# app/web.py
from __future__ import annotations

import asyncio
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import ApplicationBuilder

from .config import load_settings
from .db import init_db
from .handlers import register as register_handlers

# Загружаем конфиг и инициализируем БД
settings = load_settings()
init_db(settings.database_url)

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


@app.on_event("startup")
async def on_startup():
    await tg_app.initialize()
    await tg_app.start()

    # Устанавливаем вебхук с секретом из конфига
    url = f"{settings.base_url}{settings.webhook_path}"
    await tg_app.bot.set_webhook(url, secret_token=settings.telegram_webhook_secret)

    # Стартуем фонового вочера TON (если есть)
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
