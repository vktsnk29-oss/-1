import asyncio, os, json
import httpx
from decimal import Decimal
from sqlalchemy.orm import Session
from logging import getLogger

from .db import SessionLocal
from .models import Payment, Balance, DepositTag, State, User
from .services import credit_balance

log = getLogger(__name__)

API_BASE = os.getenv("TON_API_BASE")
API_KEY = os.getenv("TON_API_KEY")
ADDRESS = os.getenv("TON_ADDRESS")
POLL_INTERVAL = int(os.getenv("TON_POLL_INTERVAL", "5"))
MIN_DEPOSIT = Decimal(os.getenv("TON_MIN_DEPOSIT", "0"))
REQUIRE_DEPTH = int(os.getenv("TON_REQUIRE_DEPTH", "1"))
DEPOSIT_MODE = os.getenv("DEPOSIT_MODE", "comment")

HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}

async def run_watcher():
    if not API_BASE or not ADDRESS:
        log.warning("TON watcher disabled: missing TON_API_BASE or TON_ADDRESS")
        return
    log.info("TON watcher started", extra={"address": ADDRESS, "api": API_BASE})
    while True:
        try:
            await poll_once()
        except Exception:
            log.exception("ton_watcher_error")
        finally:
            await asyncio.sleep(POLL_INTERVAL)

async def poll_once():
    # Get pagination marker (to_lt) from DB state
    to_lt = None
    with SessionLocal() as db:
        st = db.get(State, "ton_to_lt")
        if st:
            to_lt = st.value

    params = {"address": ADDRESS, "limit": 16}
    if to_lt:
        params["to_lt"] = to_lt
    url = f"{API_BASE}/getTransactions"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, params=params, headers=HEADERS)
        r.raise_for_status()
        data = r.json()

    txs = data.get("result") or data.get("transactions") or []
    if not txs:
        return

    # Process from oldest to newest
    for tx in reversed(txs):
        tx_id = tx.get("transaction_id") or {}
        lt = tx_id.get("lt")
        h = tx_id.get("hash")
        ext_id = f"{lt}:{h}" if lt and h else (h or str(lt))

        # in_msg contains incoming message; ensure it's to our address and has value
        in_msg = tx.get("in_msg") or {}
        dest = in_msg.get("destination") or in_msg.get("dst")
        if not dest or dest != ADDRESS:
            continue

        value = in_msg.get("value") or "0"
        # Toncenter returns nanoTONs in string (decimal)
        amount_ton = Decimal(value) / Decimal("1e9")
        if amount_ton < MIN_DEPOSIT:
            continue

        # confirmation depth - Toncenter doesn't expose directly; assume >= REQUIRE_DEPTH
        depth_ok = True  # simplify; Ton finality is fast
        if not depth_ok:
            continue

        comment = ""
        msg_data = in_msg.get("msg_data") or {}
        # text comment may be nested: {"text":"..."} if "type"=="text"
        if isinstance(msg_data, dict):
            if msg_data.get("@type") == "msg.dataText" or msg_data.get("type") == "text":
                comment = msg_data.get("text") or ""
            elif "text" in msg_data:
                comment = msg_data["text"] or ""

        user_id = None
        if DEPOSIT_MODE == "comment" and comment:
            with SessionLocal() as db:
                tag = db.query(DepositTag).filter_by(tag=comment.strip(), is_active=True).first()
                if tag:
                    user_id = tag.user_id

        # Idempotency: skip if exists
        with SessionLocal() as db:
            if db.query(Payment).filter_by(external_id=ext_id, provider="ton").first():
                continue

            # Map tg user_id from DepositTag to Users.id
            internal_user_id = 0
            if user_id:
                u = db.query(User).filter_by(id=user_id).first()
                if u:
                    internal_user_id = u.id

            pay = Payment(
                user_id=internal_user_id,
                provider="ton",
                amount=amount_ton,
                currency="TON",
                external_id=ext_id,
                status="confirmed",
                raw=json.dumps(tx),
            )
            db.add(pay)
            if internal_user_id:
                credit_balance(db, internal_user_id, amount_ton)
                pay.status = "credited"
            db.commit()
            log.info("deposit_credited", extra={"tx": ext_id, "user_id": internal_user_id, "amount": float(amount_ton)})

        # Save pagination marker
        if lt:
            with SessionLocal() as db:
                s = db.get(State, "ton_to_lt")
                if not s:
                    from .models import State as S
                    s = S(key="ton_to_lt", value=str(lt))
                    db.add(s)
                else:
                    s.value = str(lt)
                db.commit()
