# app/handlers.py
from __future__ import annotations

import secrets
import string
from urllib.parse import quote

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, Application

from .config import load_settings

settings = load_settings()


def _gen_tag(prefix: str = "P4V") -> str:
    # короткий человеко-читаемый тег без спецсимволов
    alphabet = string.ascii_lowercase + string.digits
    rnd = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"{prefix}-{rnd}"


def build_deposit_keyboard(address: str, tag: str) -> InlineKeyboardMarkup:
    # Tonkeeper через универсальную HTTPS-ссылку (Telegram пропускает)
    tonkeeper_url = f"https://app.tonkeeper.com/transfer/{address}?text={quote(tag)}"
    # Официальный кошелёк Telegram (адрес и тег показываем в тексте)
    tg_wallet_url = "https://t.me/wallet"

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔵 Tonkeeper (рекомендуется)", url=tonkeeper_url)],
            [InlineKeyboardButton("💠 Telegram Wallet", url=tg_wallet_url)],
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_message(
        "Привет! Это бот пополнения через TON.\n"
        "Нажми /deposit чтобы получить адрес и метку платежа.",
    )


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tag = _gen_tag(settings.deposit_tag_prefix)
    address = settings.ton_address

    text = (
        "💳 *Пополнение TON*\n\n"
        f"1) Отправь TON на адрес:\n`{address}`\n"
        f"2) *Обязательно укажи комментарий:* `{tag}`\n\n"
        "_Или используй кнопку для Tonkeeper ниже._"
    )

    await update.effective_chat.send_message(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=build_deposit_keyboard(address, tag),
        disable_web_page_preview=True,
    )


async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # на будущее — безопасный обработчик, чтобы не падать
    q = update.callback_query
    if q:
        await q.answer("Ок")  # просто закрываем спиннер


def register(app: Application) -> None:
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CallbackQueryHandler(on_cb))
