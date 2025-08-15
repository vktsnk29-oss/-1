import asyncio
from typing import Any, Dict, List, Optional

import httpx

try:
    import structlog
    log = structlog.get_logger()
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("ton_watcher")

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import load_settings
from .models import State

settings = load_settings()


# --- DB session helper -------------------------------------------------------
def _make_session_factory():
    try:
        from .db import SessionLocal  # если уже есть фабрика в проекте
        return SessionLocal
    except Exception:
        engine = create_engine(str(settings.database_url), pool_pre_ping=True, future=True)
        return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


SessionLocal = _make_session_factory()


# --- Toncenter API -----------------------------------------------------------
async def _get_transactions(
    address: str,
    limit: int = 16,
    to_lt: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Вызов Toncenter getTransactions:
      - X-API-Key в заголовке,
      - api_key в query (на всякий случай),
      - archival=true,
      - короткий retry на 5xx.
    Возвращает список транзакций из data['result'].
    """
    base = str(settings.ton_api_base).rstrip("/")  # <-- ключевая правка: str(...)
    # допускаем как https://toncenter.com/api так и /api/v2
    if base.endswith("/v2"):
        url = f"{base}/getTransactions"
    else:
        url = f"{base}/v2/getTransactions"

    params: Dict[str, Any] = {
        "address": address,
        "limit": limit,
        "archival": "true",
    }
    if to_lt:
        params["to_lt"] = to_lt

    headers: Dict[str, str] = {}
    if getattr(settings, "ton_api_key", None):
        headers["X-API-Key"] = settings.ton_api_key
        params["api_key"] = settings.ton_api_key  # дублируем — Toncenter это принимает

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, params=params, headers=headers)
        if 500 <= r.status_code < 600:
            await asyncio.sleep(1.5)
            r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()

    if isinstance(data, dict):
        return data.get("result", []) or []
    return []


# --- State helpers -----------------------------------------------------------
def _get_to_lt(db: Session) -> Optional[str]:
    st = db.get(State, "ton_to_lt")
    return (st.value if st else None) or None


def _set_to_lt(db: Session, new_lt: str) -> None:
    st = db.get(State, "ton_to_lt")
    if st is None:
        st = State(key="ton_to_lt", value=new_lt)
        db.add(st)
    else:
        st.value = new_lt
    db.commit()


def _extract_max_lt(txs: List[Dict[str, Any]]) -> Optional[str]:
    lts: List[int] = []
    for tx in txs:
        lt = None
        tid = tx.get("transaction_id") or {}
        if isinstance(tid, dict):
            lt = tid.get("lt") or tid.get("logical_time")
        if lt is None:
            lt = tx.get("lt")
        if lt is None:
            continue
        try:
            lts.append(int(str(lt)))
        except Exception:
            continue
    if not lts:
        return None
    return str(max(lts))


# --- Poll loop ---------------------------------------------------------------
async def poll_once() -> None:
    with SessionLocal() as db:
        to_lt = _get_to_lt(db)
        txs = await _get_transactions(settings.ton_address, limit=16, to_lt=to_lt)
        if not txs:
            return

        max_lt = _extract_max_lt(txs)
        if max_lt:
            _set_to_lt(db, max_lt)

        try:
            log.info("ton_watcher_tx_batch", count=len(txs), new_to_lt=max_lt)
        except Exception:
            pass


async def run_watcher() -> None:
    await asyncio.sleep(0.5)  # даём подняться приложению
    while True:
        try:
            await poll_once()
        except Exception as e:
            try:
                log.error("ton_watcher_error", error=str(e))
            except Exception:
                print("ton_watcher_error", e)
            await asyncio.sleep(2.0)
        await asyncio.sleep(3.0)
