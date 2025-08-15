import secrets, string
from sqlalchemy.orm import Session
from .models import DepositTag, Balance

ALPH = string.ascii_uppercase + string.digits

def gen_tag(prefix: str = "P4V", length: int = 6) -> str:
    return f"{prefix}-{''.join(secrets.choice(ALPH) for _ in range(length))}"

def get_or_create_tag(db: Session, user_id: int, prefix: str = "P4V") -> str:
    tag = db.query(DepositTag).filter_by(user_id=user_id, is_active=True).first()
    if tag:
        return tag.tag
    t = gen_tag(prefix=prefix)
    while db.query(DepositTag).filter_by(tag=t).first():
        t = gen_tag(prefix=prefix)
    db.add(DepositTag(user_id=user_id, tag=t))
    db.commit()
    return t

def credit_balance(db: Session, user_id: int, amount):
    row = db.query(Balance).filter_by(user_id=user_id).first()
    if row:
        row.amount = (row.amount or 0) + amount
    else:
        db.add(Balance(user_id=user_id, amount=amount))
