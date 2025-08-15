# app/handlers.py
from __future__ import annotations

import os
from typing import Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# === ENV ===
TON_ADDRESS = os.getenv("TON_ADDRESS", "")
MIN_DEPOSIT = os.getenv("TON_MIN_DEPOSIT", "0.1")
DEFAULT_DEPOSIT_AMOUNT = os.getenv("DEFAULT_DEPOSIT_AMOUNT", "0")  # "0" -> не подставлять
DEPOSIT_TAG_PREFIX = os.getenv("DEPOSIT_TAG_PREFIX", "P4V")


# === UI ===
def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💳 Пополнить", callback_data="deposit"),
                InlineKeyboardButton("💰 Баланс", callback_data="balance"),
            ],
            [
                InlineKeyboardButton("💸 Вывод", callback_data="withdraw"),
                InlineKeyboardButton("👥 Рефералы", callback_data="ref"),
            ],
            [InlineKeyboardButton("ℹ️ О нас", callback_data="about")],
        ]
    )


def payment_keyboard(address: str, tag: str, amount: Optional[str]) -> InlineKeyboardMarkup:
    """
    Кнопки deeplink для Tonkeeper / Telegram Wallet и универсальная ton:// ссылка.
    amount — строка (например "5"), "0" или None = не подставлять сумму.
    """
    amt_q = f"&amount={amount}" if amount and amount != "0" else ""
    ton_universal = f"ton://transfer/{address}?text={tag}{amt_q}"
    tonkeeper = f"tonkeeper://transfer/{address}?text={tag}{amt_q}"
    tg_wallet = (
        f"https://t.me/wallet/start?startapp=send"
        f"&asset=TON&address={address}{amt_q}&comment={tag}"
    )
    kb = [
        [InlineKeyboardButton("🚀 Оплатить (универсальная)", url=ton_universal)],
        [
            InlineKeyboardButton("📱 Tonkeeper", url=tonkeeper),
            InlineKeyboardButton("💼 Telegram Wallet", url=tg_wallet),
        ],
    ]
    return InlineKeyboardMarkup(kb)


# === Helpers ===
def _base36(n: int) -> str:
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if n == 0:
        return "0"
    s = []
    x = abs(n)
    while x:
        x, r = divmod(x, 36)
        s.append(chars[r])
    return ("-" if n < 0 else "") + "".join(reversed(s))


def get_or_create_deposit_tag(user_id: int, prefix: str = DEPOSIT_TAG_PREFIX) -> str:
    """
    Пытаемся взять тег из БД (таблица deposit_tags), если есть.
    Если сервиса или таблицы нет — даём детерминированный тег по user_id.
    """
    try:
        from app.db import SessionLocal  # type: ignore
        from app.models import DepositTag  # type: ignore[attr-defined]
    except Exception:
        # Фолбэк: детерминированный тег без БД
        return f"{prefix}-{_base36(user_id)}"

    try:
        with SessionLocal() as db:
            row = db.query(DepositTag).filter_by(user_id=user_id, is_active=True).first()
            if row:
                return row.tag

            # генерим новый и гарантируем уникальность
            import secrets, string

            ALPH = string.ascii_uppercase + string.digits
            def gen() -> str:
                return f"{prefix}-" + "".join(secrets.choice(ALPH) for _ in range(6))

            tag = gen()
            while db.query(DepositTag).filter_by(tag=tag).first():
                tag = gen()

            db.add(DepositTag(user_id=user_id, tag=tag, is_active=True))
            db.commit()
            return tag
    except Exception:
        # Любая ошибка с БД — безопасный фолбэк
        return f"{prefix}-{_base36(user_id)}"


async def _get_balance_text(user_id: int) -> str:
    """
    Пытаемся прочитать баланс из БД (таблица balances). Если нет — 0.00 TON.
    """
    try:
        from app.db import SessionLocal  # type: ignore
        from app.models import Balance  # type: ignore[attr-defined]
    except Exception:
        return "Ваш баланс: 0.00 TON"

    try:
        with SessionLocal() as db:
            row = db.query(Balance).filter_by(user_id=user_id).first()
            amount = row.amount if row and row.amount is not None else 0
            return f"Ваш баланс: {amount} TON"
    except Exception:
        return "Ваш баланс: 0.00 TON"


# === Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # (опционально) регистрируем пользователя в БД; безопасно игнорируем ошибки
    try:
        from app.db import SessionLocal  # type: ignore
        from app.models import User  # type: ignore[attr-defined]
        from sqlalchemy import select  # type: ignore
        tg_id = update.effective_user.id
        with SessionLocal() as db:
            exists = db.execute(select(User).where(User.tg_id == tg_id)).scalar_one_or_none()
            if not exists:
                u = User(tg_id=tg_id, language=(update.effective_user.language_code or "ru"))
                db.add(u)
                db.commit()
    except Exception:
        pass

    await update.effective_message.reply_text(
        "Привет! Это прод-бот. Выбирай действие:", reply_markup=main_keyboard()
    )


async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "balance":
        text = await _get_balance_text(update.effective_user.id)
        await q.edit_message_text(text, reply_markup=main_keyboard())

    elif data == "about":
        await q.edit_message_text(
            "Мы — сервис с приёмом TON. Пополнение через комментарий (депозит-тег).",
            reply_markup=main_keyboard(),
        )

    elif data == "deposit":
        tag = get_or_create_deposit_tag(update.effective_user.id, DEPOSIT_TAG_PREFIX)
        text = (
            f"💳 *Пополнение TON*\n\n"
            f"1) Отправьте TON на адрес:\n`{TON_ADDRESS}`\n"
            f"2) Укажите комментарий (обязательно):\n`{tag}`\n"
            f"3) Минимальная сумма: *{MIN_DEPOSIT} TON*\n\n"
            f"Зачисление происходит автоматически после подтверждения сети."
        )
        await q.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=payment_keyboard(TON_ADDRESS, tag, DEFAULT_DEPOSIT_AMOUNT),
        )

    elif data == "withdraw":
        await q.edit_message_text(
            "Заявка на вывод: отправьте сумму и адрес (заглушка).",
            reply_markup=main_keyboard(),
        )

    elif data == "ref":
        # Заглушка. Здесь можно подставить реальную ссылку: t.me/<bot>?start=<ref>
        await q.edit_message_text(
            "Ваша реферальная ссылка: t.me/your_bot?start=ref123",
            reply_markup=main_keyboard(),
        )

    else:
        await q.edit_message_text("Неизвестная команда.", reply_markup=main_keyboard())


def register(app: Application):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_cb))
