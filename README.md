# Telegram Bot (Webhook) + TON Deposits (Toncenter)

- FastAPI webhook + python-telegram-bot 22.x
- PostgreSQL (SQLAlchemy/Alembic)
- TON watcher via Toncenter (incoming transfers by comment tag)
- Payment buttons: ton://, tonkeeper://, Telegram Wallet (TON Space)

## Run
1) Copy `.env.example` to `.env`, fill values.
2) `pip install -r requirements.txt`
3) `alembic upgrade head`
4) `uvicorn app.web:app --host 0.0.0.0 --port 8080`

## ENV essentials
- BOT_TOKEN, BASE_URL, TELEGRAM_WEBHOOK_SECRET
- DATABASE_URL
- TON_API_BASE, TON_API_KEY, TON_ADDRESS
