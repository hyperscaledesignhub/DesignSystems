from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from decimal import Decimal
from shared.utils.database import Base
import uuid

class WalletDB(Base):
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    currency = Column(String, default="USD", nullable=False)
    available_balance = Column(Numeric(precision=20, scale=8), default=Decimal("0"))
    blocked_balance = Column(Numeric(precision=20, scale=8), default=Decimal("0"))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class TransactionDB(Base):
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(Integer, nullable=False)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    transaction_type = Column(String, nullable=False)  # DEPOSIT, WITHDRAWAL, TRADE_BUY, TRADE_SELL, BLOCK, UNBLOCK
    reference_id = Column(UUID(as_uuid=True))  # order_id or external reference
    description = Column(String)
    balance_after = Column(Numeric(precision=15, scale=2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())