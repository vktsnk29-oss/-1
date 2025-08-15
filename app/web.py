import os, asyncio
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import ApplicationBuilder
from .config import load_settings
from .handlers import register as register_handlers
from .db import init_db
from .ton_watch import run_watcher

settings = load_settings()
init_db(settings.database_url)

app = FastAPI(title="TG Bot Webhook")

application = ApplicationBuilder().token(settings.bot_token.get_secret_value()).build()
register_handlers(application)

_watcher_task = None

@app.on_event("startup")
async def on_startup():
    await application.initialize()
    await application.start()
    # Set webhook with secret token
    await application.bot.set_webhook(
        url=f"{settings.base_url}{settings.webhook_path}",
        secret_token=settings.webhook_secret,
    )
    global _watcher_task
    _watcher_task = asyncio.create_task(run_watcher())

@app.on_event("shutdown")
async def on_shutdown():
    if _watcher_task:
        _watcher_task.cancel()
    await application.stop()
    await application.shutdown()

@app.post(settings.webhook_path)
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(None)):
    # Verify secret token
    if x_telegram_bot_api_secret_token != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return JSONResponse({"ok": True})

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
