from pydantic import BaseModel, Field, SecretStr, AnyUrl
from typing import List, Optional
import os

class Settings(BaseModel):
    app_env: str = Field(default="production", alias="APP_ENV")
    bot_token: SecretStr = Field(alias="BOT_TOKEN")
    base_url: AnyUrl = Field(alias="BASE_URL")
    webhook_path: str = Field(default="/webhook/telegram", alias="WEBHOOK_PATH")
    webhook_secret: str = Field(alias="TELEGRAM_WEBHOOK_SECRET")
    port: int = Field(default=int(os.getenv("PORT", "8080")))
    admin_ids: List[int] = Field(default_factory=list, alias="ADMIN_IDS")

    database_url: str = Field(alias="DATABASE_URL")

    ton_provider: str = Field(default="toncenter", alias="TON_PROVIDER")
    ton_api_base: str = Field(alias="TON_API_BASE")
    ton_api_key: Optional[str] = Field(default=None, alias="TON_API_KEY")
    ton_address: str = Field(alias="TON_ADDRESS")
    ton_poll_interval: int = Field(default=5, alias="TON_POLL_INTERVAL")
    ton_min_deposit: float = Field(default=0.0, alias="TON_MIN_DEPOSIT")
    ton_require_depth: int = Field(default=1, alias="TON_REQUIRE_DEPTH")
    deposit_mode: str = Field(default="comment", alias="DEPOSIT_MODE")
    deposit_tag_prefix: str = Field(default="P4V", alias="DEPOSIT_TAG_PREFIX")
    default_deposit_amount: float = Field(default=0.0, alias="DEFAULT_DEPOSIT_AMOUNT")

    class Config:
        populate_by_name = True
        extra = "ignore"

def load_settings():
    from dotenv import load_dotenv
    load_dotenv()
    admins = os.getenv("ADMIN_IDS", "")
    os.environ["ADMIN_IDS"] = ",".join([a.strip() for a in admins.replace(";", ",").split(",") if a.strip().isdigit()])
    return Settings()
