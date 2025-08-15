from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, Application
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import User, Balance
from .services import get_or_create_tag
import os

MAIN_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("💳 Пополнить", callback_data="deposit"),
     InlineKeyboardButton("💰 Баланс", callback_data="balance")],
    [InlineKeyboardButton("💸 Вывод", callback_data="withdraw"),
     InlineKeyboardButton("👥 Рефералы", callback_data="ref")],
    [InlineKeyboardButton("ℹ️ О нас", callback_data="about")]
])

def payment_keyboard(address: str, amount: float | None, tag: str) -> InlineKeyboardMarkup:
    amt = f"&amount={amount}" if amount and amount > 0 else ""
    # universal ton://
    ton_universal = f"ton://transfer/{address}?{'amount='+str(amount)+'&' if amount and amount>0 else ''}text={tag}"
    tonkeeper = f"tonkeeper://transfer/{address}?{'amount='+str(amount)+'&' if amount and amount>0 else ''}text={tag}"
    tg_wallet = f"https://t.me/wallet/start?startapp=send&asset=TON&address={address}{amt}&comment={tag}"
    kb = [
        [InlineKeyboardButton("🚀 Оплатить (универсальная)", url=ton_universal)],
        [InlineKeyboardButton("📱 Tonkeeper", url=tonkeeper),
         InlineKeyboardButton("💼 Telegram Wallet", url=tg_wallet)],
    ]
    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # user register
    with SessionLocal() as db:
        u = db.query(User).filter_by(tg_id=update.effective_user.id).first()
        if not u:
            u = User(tg_id=update.effective_user.id, language=(update.effective_user.language_code or "ru"))
            db.add(u); db.commit()
    await update.effective_message.reply_text(
        "Привет! Это прод-бот. Выбирай действие:", reply_markup=MAIN_KB
    )

async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    data = q.data
    if data == "balance":
        with SessionLocal() as db:
            u = db.query(User).filter_by(tg_id=update.effective_user.id).first()
            bal = db.query(Balance).filter_by(user_id=u.id).first()
            amount = bal.amount if bal else 0
        await q.edit_message_text(f"Ваш баланс: {amount} TON", reply_markup=MAIN_KB)
    elif data == "about":
        await q.edit_message_text("Мы — облачный сервис. Пополняйте TON, средства учитываются автоматически.", reply_markup=MAIN_KB)
    elif data == "deposit":
        address = os.getenv("TON_ADDRESS", "EQ...")
        amount = float(os.getenv("DEFAULT_DEPOSIT_AMOUNT", "0"))
        with SessionLocal() as db:
            u = db.query(User).filter_by(tg_id=update.effective_user.id).first()
            tag = get_or_create_tag(db, user_id=u.id, prefix=os.getenv("DEPOSIT_TAG_PREFIX","P4V"))
        text = (
            "💳 *Пополнение TON*

"
            f"1) Отправьте TON на адрес:
`{address}`
"
            f"2) Укажите комментарий (обязательно):
`{tag}`
"
            "Зачисление происходит автоматически после подтверждения сети."
        )
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=payment_keyboard(address, amount if amount>0 else None, tag))
    elif data == "withdraw":
        await q.edit_message_text("Заявка на вывод: отправьте сумму и адрес (заглушка).", reply_markup=MAIN_KB)
    elif data == "ref":
        await q.edit_message_text("Ваша реферальная ссылка: t.me/your_bot?start=ref123 (заглушка)", reply_markup=MAIN_KB)
    else:
        await q.edit_message_text("Неизвестная команда.", reply_markup=MAIN_KB)

def register(app: Application):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_cb))
