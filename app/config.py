# app/config.py
from __future__ import annotations

import os
from decimal import Decimal
from typing import List

from pydantic import Field, SecretStr, AnyUrl, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # читаем ENV и .env; игнорим лишние поля
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Telegram / bot
    bot_token: SecretStr = Field(validation_alias=AliasChoices("BOT_TOKEN", "bot_token"))
    app_env: str = Field(default="production", validation_alias=AliasChoices("APP_ENV", "app_env"))
    base_url: AnyUrl = Field(validation_alias=AliasChoices("BASE_URL", "base_url"))
    port: int = Field(default=8080, validation_alias=AliasChoices("PORT", "port"))
    webhook_path: str = Field(default="/webhook/telegram", validation_alias=AliasChoices("WEBHOOK_PATH", "webhook_path"))
    telegram_webhook_secret: str = Field(validation_alias=AliasChoices("TELEGRAM_WEBHOOK_SECRET", "telegram_webhook_secret"))
    admin_ids: List[int] = Field(default_factory=list, validation_alias=AliasChoices("ADMIN_IDS", "admin_ids"))

    # DB
    database_url: str = Field(validation_alias=AliasChoices("DATABASE_URL", "database_url"))

    # TON watcher
    ton_api_base: AnyUrl = Field(validation_alias=AliasChoices("TON_API_BASE", "ton_api_base"))
    ton_api_key: str = Field(validation_alias=AliasChoices("TON_API_KEY", "ton_api_key"))
    ton_address: str = Field(validation_alias=AliasChoices("TON_ADDRESS", "ton_address"))
    ton_poll_interval: int = Field(default=5, validation_alias=AliasChoices("TON_POLL_INTERVAL", "ton_poll_interval"))
    ton_min_deposit: Decimal = Field(default=Decimal("0"), validation_alias=AliasChoices("TON_MIN_DEPOSIT", "ton_min_deposit"))
    ton_require_depth: int = Field(default=1, validation_alias=AliasChoices("TON_REQUIRE_DEPTH", "ton_require_depth"))
    deposit_mode: str = Field(default="comment", validation_alias=AliasChoices("DEPOSIT_MODE", "deposit_mode"))
    deposit_tag_prefix: str = Field(default="P4V", validation_alias=AliasChoices("DEPOSIT_TAG_PREFIX", "deposit_tag_prefix"))
    default_deposit_amount: str = Field(default="0", validation_alias=AliasChoices("DEFAULT_DEPOSIT_AMOUNT", "default_deposit_amount"))


def load_settings() -> Settings:
    # Разрешаем подтягивать .env локально
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    # Фолбэк BASE_URL из Render
    if not os.getenv("BASE_URL") and os.getenv("RENDER_EXTERNAL_URL"):
        os.environ["BASE_URL"] = os.getenv("RENDER_EXTERNAL_URL")

    # Нормализуем ADMIN_IDS в JSON-массив, чтобы Pydantic однозначно разобрал
    admins = os.getenv("ADMIN_IDS", "")
    nums = [a.strip() for a in admins.replace(";", ",").split(",") if a.strip().isdigit()]
    if nums:
        os.environ["ADMIN_IDS"] = "[" + ",".join(nums) + "]"
    else:
        # если пусто/мусор — убираем переменную, чтобы сработал default_factory=list
        if "ADMIN_IDS" in os.environ:
            del os.environ["ADMIN_IDS"]

    # Дефолт порта, если не задан
    os.environ.setdefault("PORT", "8080")

    return Settings()
