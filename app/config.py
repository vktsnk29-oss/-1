# app/config.py
from __future__ import annotations
from pydantic import BaseModel, Field, SecretStr, AnyUrl
from decimal import Decimal
from typing import List
import os

class Settings(BaseModel):
    # Telegram/bot
    bot_token: SecretStr = Field(alias="BOT_TOKEN")
    app_env: str = Field(default="production", alias="APP_ENV")
    base_url: AnyUrl = Field(alias="BASE_URL")
    port: int = Field(default=int(os.getenv("PORT", "8080")))
    webhook_path: str = Field(default="/webhook/telegram", alias="WEBHOOK_PATH")
    telegram_webhook_secret: str = Field(alias="TELEGRAM_WEBHOOK_SECRET")
    admin_ids: List[int] = Field(default_factory=list, alias="ADMIN_IDS")

    # DB
    database_url: str = Field(alias="DATABASE_URL")

    # TON watcher
    ton_api_base: AnyUrl = Field(alias="TON_API_BASE")
    ton_api_key: str = Field(alias="TON_API_KEY")
    ton_address: str = Field(alias="TON_ADDRESS")
    ton_poll_interval: int = Field(default=int(os.getenv("TON_POLL_INTERVAL", "5")))
    ton_min_deposit: Decimal = Field(default=Decimal(os.getenv("TON_MIN_DEPOSIT", "0")))
    ton_require_depth: int = Field(default=int(os.getenv("TON_REQUIRE_DEPTH", "1")))
    deposit_mode: str = Field(default=os.getenv("DEPOSIT_MODE", "comment"))
    deposit_tag_prefix: str = Field(default=os.getenv("DEPOSIT_TAG_PREFIX", "P4V"))
    default_deposit_amount: str = Field(default=os.getenv("DEFAULT_DEPOSIT_AMOUNT", "0"))

    class Config:
        populate_by_name = True
        extra = "ignore"

def load_settings() -> Settings:
    from dotenv import load_dotenv
    load_dotenv()

    # Фолбэк: BASE_URL из переменной Render, если не задан вручную
    if not os.getenv("BASE_URL") and os.getenv("RENDER_EXTERNAL_URL"):
        os.environ["BASE_URL"] = os.getenv("RENDER_EXTERNAL_URL")

    # Нормализуем ADMIN_IDS в список чисел
    admins = os.getenv("ADMIN_IDS", "")
    os.environ["ADMIN_IDS"] = ",".join(
        [a.strip() for a in admins.replace(";", ",").split(",") if a.strip().isdigit()]
    )
    return Settings()
