from __future__ import annotations

import asyncio
import base64
import contextlib
from typing import Optional

import structlog
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse, Response, PlainTextResponse
from telegram import Update
from telegram.ext import Application

from .config import load_settings
from .handlers import register as register_handlers
from .ton_watch import run_watcher

logger = structlog.get_logger()

app = FastAPI()
settings = load_settings()


def _secret(val):
    """Возвращает str из SecretStr/None/str без утечек."""
    if val is None:
        return None
    get = getattr(val, "get_secret_value", None)
    return get() if callable(get) else val


# ===== Telegram Bot (python-telegram-bot v22) =====
_bot_token = _secret(settings.bot_token)  # <-- ВАЖНО: превратили SecretStr в str
tg_app: Application = Application.builder().token(_bot_token).build()
register_handlers(tg_app)

# ======= Webhook endpoint =======
@app.post(getattr(settings, "webhook_path", "/webhook/telegram"))
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
):
    # Проверка секрета вебхука
    expected = _secret(getattr(settings, "webhook_secret", None))
    if expected and x_telegram_bot_api_secret_token != expected:
        raise HTTPException(status_code=403, detail="invalid webhook secret")

    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return PlainTextResponse("OK")


# ======= LIFECYCLE =======
@app.on_event("startup")
async def on_startup():
    # Устанавливаем Telegram Webhook
    base = str(settings.base_url).rstrip("/")
    webhook_url = base + getattr(settings, "webhook_path", "/webhook/telegram")
    await tg_app.bot.set_webhook(
        url=webhook_url,
        secret_token=_secret(getattr(settings, "webhook_secret", None)),
        drop_pending_updates=True,
    )
    logger.info("webhook_set", url=webhook_url)

    # Стартуем TON watcher в фоне
    app.state._ton_task = asyncio.create_task(_run_watcher_safe())


@app.on_event("shutdown")
async def on_shutdown():
    task: asyncio.Task | None = getattr(app.state, "_ton_task", None)
    if task and not task.done():
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


async def _run_watcher_safe():
    try:
        await run_watcher()
    except Exception as e:
        logger.error("ton_watcher_error", error=str(e))


# ======= Простая главная =======
@app.get("/", response_class=PlainTextResponse)
def root():
    return "ok"


# ======= TON Connect: manifest + icon + pay page =======

# 1x1 PNG (прозрачная), чтобы не возиться со статикой
_ICON_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)

@app.get("/icon.png")
def tonconnect_icon():
    data = base64.b64decode(_ICON_B64)
    return Response(content=data, media_type="image/png")


@app.get("/tonconnect-manifest.json", response_class=JSONResponse)
def tonconnect_manifest():
    base = str(settings.base_url).rstrip("/")
    return {
        "url": base,
        "name": "Bot Payments",
        "iconUrl": f"{base}/icon.png",
    }


@app.get("/pay", response_class=HTMLResponse)
def pay(amount: float, memo: str = "", to: Optional[str] = None):
    """
    Страница оплаты через TON Connect.
    GET-параметры:
      - amount: сумма в TON (float), напр. 2.5
      - memo: произвольный комментарий (не обязателен)
      - to: адрес получателя (если не указан — берём из настроек)
    """
    to_addr = to or settings.ton_address
    base = str(settings.base_url).rstrip("/")

    # Встраиваемый HTML — открывает модалку TON Connect и отправляет транзакцию
    html = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="ton-connect-manifest" content="{base}/tonconnect-manifest.json" />
  <title>Оплата через TON Connect</title>
  <style>
    body {{ font-family: system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,'Helvetica Neue',Arial; padding: 24px; max-width: 680px; margin: 0 auto; }}
    .card {{ border: 1px solid #e5e7eb; border-radius: 16px; padding: 20px; }}
    .row {{ margin: 8px 0; }}
    button {{ padding: 12px 16px; border-radius: 12px; border: none; cursor: pointer; }}
    #connect {{ background: #111827; color: white; }}
    #paybtn {{ background: #2563eb; color: white; }}
    .muted {{ color: #6b7280; font-size: 14px; }}
    .addr {{ font-family: ui-monospace, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }}
  </style>
</head>
<body>
  <h1>Оплата через TON Connect</h1>
  <div class="card">
    <div class="row">Получатель: <span class="addr">{to_addr}</span></div>
    <div class="row">Сумма: <b id="amt">{amount}</b> TON</div>
    <div class="row">Комментарий: <span id="memo">{memo or "—"}</span></div>
    <div class="row muted">Выберите кошелёк и подтвердите перевод.</div>
    <div class="row" style="display:flex; gap:10px; margin-top:16px;">
      <button id="connect">Подключить кошелёк</button>
      <button id="paybtn">Оплатить</button>
    </div>
    <div class="row muted" id="status" style="margin-top:12px;"></div>
  </div>

  <script type="module">
    import {{ TonConnectUI }} from "https://unpkg.com/@tonconnect/ui@latest/dist/tonconnect-ui.min.js";

    const manifestUrl = "{base}/tonconnect-manifest.json";
    const tonConnectUI = new TonConnectUI({{ manifestUrl }});

    const toAddr = "{to_addr}";
    const amountTON = {amount};
    const memo = {memo!r};

    // TON -> nanoTON
    const amountNano = BigInt(Math.round(amountTON * 1e9)).toString();

    const statusEl = document.getElementById("status");
    const setStatus = (t) => statusEl.textContent = t;

    document.getElementById("connect").onclick = async () => {{
      try {{
        await tonConnectUI.openModal();
      }} catch (e) {{
        setStatus("Не удалось открыть список кошельков: " + e);
      }}
    }};

    function buildTx() {{
      return {{
        validUntil: Math.floor(Date.now()/1000) + 600,
        messages: [{{
          address: toAddr,
          amount: amountNano
          // payload: addCommentPayload(memo) // включи, если хочешь писать комментарий в блокчейн
        }}]
      }};
    }}

    // Пример добавления комментария (опционально):
    // import {{ beginCell }} from "https://unpkg.com/@ton/core@latest/dist/index.js";
    // function addCommentPayload(text) {{
    //   if (!text) return undefined;
    //   const cell = beginCell().storeUint(0, 32).storeStringTail(text).endCell();
    //   return cell.toBoc({{ idx: false }}).toString("base64");
    // }}

    document.getElementById("paybtn").onclick = async () => {{
      try {{
        if (!tonConnectUI.account) {{
          await tonConnectUI.openModal();
        }}
        const tx = buildTx();
        await tonConnectUI.sendTransaction(tx);
        setStatus("Запрос на транзакцию отправлен в кошелёк.");
      }} catch (e) {{
        setStatus("Ошибка: " + (e?.message || e));
      }}
    }};
  </script>
</body>
</html>
"""
    return HTMLResponse(html)
