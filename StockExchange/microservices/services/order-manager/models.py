from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from shared.utils.database import Base
from shared.models.base import OrderSide, OrderStatus, OrderType
import uuid

class OrderDB(Base):
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)  # BUY or SELL
    order_type = Column(String, nullable=False)  # MARKET or LIMIT
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(precision=15, scale=2), nullable=False)
    filled_quantity = Column(Integer, default=0)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ExecutionDB(Base):
    __tablename__ = "executions"
    
    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    side = Column(SQLEnum(OrderSide), nullable=False)
    quantity = Column(Numeric(precision=20, scale=8), nullable=False)
    price = Column(Numeric(precision=20, scale=8), nullable=False)
    buyer_id = Column(Integer, nullable=False)
    seller_id = Column(Integer, nullable=False)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())