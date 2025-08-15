from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, String, Integer, DateTime, func, Numeric, Boolean, Text
from .db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="ru")
    referrer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False) # ton
    amount: Mapped[float] = mapped_column(Numeric(18,8), nullable=False)
    currency: Mapped[str] = mapped_column(String(12), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False) # tx hash or lt:hash
    status: Mapped[str] = mapped_column(String(24), default="pending")
    raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())

class Balance(Base):
    __tablename__ = "balances"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    amount: Mapped[float] = mapped_column(Numeric(18,8), default=0)

class Withdrawal(Base):
    __tablename__ = "withdrawals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18,8), nullable=False)
    address: Mapped[str] = mapped_column(String(256), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(24), default="pending")
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped = mapped_column(DateTime(timezone=True), nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event: Mapped[str] = mapped_column(String(64))
    data: Mapped[str] = mapped_column(String(2048))
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())

class DepositTag(Base):
    __tablename__ = "deposit_tags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    tag: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())

class State(Base):
    __tablename__ = "state"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(512))
