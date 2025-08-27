from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from shared.utils.database import Base
from shared.models.base import OrderSide

class ReportDB(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String, nullable=False)  # daily_summary, monthly_summary, etc.
    user_id = Column(Integer, index=True)
    symbol = Column(String, index=True)
    data = Column(String)  # JSON data
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

class TradeReportDB(Base):
    __tablename__ = "trade_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    order_id = Column(String, nullable=False, index=True)
    execution_id = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    side = Column(SQLEnum(OrderSide), nullable=False)
    quantity = Column(Numeric(precision=20, scale=8), nullable=False)
    price = Column(Numeric(precision=20, scale=8), nullable=False)
    total_value = Column(Numeric(precision=20, scale=8), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=False, index=True)