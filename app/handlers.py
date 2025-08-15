from urllib.parse import quote

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from .config import load_settings

settings = load_settings()


def _deposit_keyboard(addr: str, comment: str) -> InlineKeyboardMarkup:
    """
    ✅ HTTPS-deeplink для Tonkeeper (Telegram запрещает tonkeeper:// в кнопках)
    ✅ Кнопка на Telegram Wallet
    """
    tk_url = f"https://app.tonkeeper.com/transfer/{addr}?text={quote(comment)}"
    tw_url = "https://t.me/wallet"

    rows = [
        [
            InlineKeyboardButton("Tonkeeper", url=tk_url),
            InlineKeyboardButton("Telegram Wallet", url=tw_url),
        ],
        # Можно добавить подсказки/проверку:
        # [InlineKeyboardButton("Показать адрес", callback_data="show_addr")],
        # [InlineKeyboardButton("Показать комментарий", callback_data=f"show_comment:{comment}")],
    ]
    return InlineKeyboardMarkup(rows)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    comment = f"user-{user.id}" if user else "deposit"

    text = (
        "💼 *Пополнение TON*\n\n"
        "Отправьте любую сумму на адрес ниже. Для корректного зачисления сохраните комментарий.\n\n"
        f"*Адрес:*\n`{settings.ton_address}`\n"
        f"*Комментарий:*\n`{comment}`"
    )
    await update.effective_message.reply_text(
        text,
        reply_markup=_deposit_keyboard(settings.ton_address, comment),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    data = q.data or ""
    # здесь можно обработать свои callback_data (show_addr / show_comment и пр.)
    if data.startswith("show_addr"):
        await q.answer()
        await q.edit_message_text(
            f"Адрес для пополнения:\n`{settings.ton_address}`",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        return

    await q.answer("Ок")


def register(app: Application) -> None:
    """
    Регистрация хендлеров. В web.py вызывается как register_handlers(application)
    """
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_cb))
