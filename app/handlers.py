from __future__ import annotations

from urllib.parse import quote

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes, CommandHandler, CallbackQueryHandler

from .config import load_settings

settings = load_settings()


def build_tonconnect_pay_kb(amount_ton: float, memo: str = "") -> InlineKeyboardMarkup:
    base = str(settings.base_url).rstrip("/")
    # Добавляем &to=..., чтобы явно передать адрес получателя
    pay_url = f"{base}/pay?amount={amount_ton}&memo={quote(memo)}&to={settings.ton_address}"
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"Оплатить {amount_ton} TON (TON Connect)", url=pay_url)]]
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Простейший стартовый хендлер с кнопкой оплаты.
    Подставь свою бизнес-логику расчёта суммы/комментария.
    """
    amount_ton = 2.5
    memo = "demo-order-123"
    kb = build_tonconnect_pay_kb(amount_ton, memo)
    text = (
        "👋 Привет! Это демо.\n\n"
        f"Сумма к оплате: <b>{amount_ton} TON</b>\n"
        f"Комментарий: <code>{memo}</code>\n\n"
        "Нажми кнопку, чтобы оплатить через TON Connect."
    )
    await update.effective_chat.send_message(text, reply_markup=kb, parse_mode="HTML")


# Если у тебя есть существующие callback-кнопки — добавь сюда нужные обработчики.
# Оставим пример для будущих расширений:
async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Окей!")


def register(app: Application):
    """
    Регистрируем хендлеры в PTB Application.
    Если у тебя есть свои — добавляй их тут.
    """
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_cb))
