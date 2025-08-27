from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
from decimal import Decimal

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class OrderType(str, Enum):
    LIMIT = "LIMIT"

class User(BaseModel):
    id: Optional[int] = None
    email: str
    username: str
    password_hash: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

class Wallet(BaseModel):
    id: Optional[int] = None
    user_id: int
    currency: str = "USD"
    available_balance: Decimal
    blocked_balance: Decimal = Decimal("0")
    updated_at: Optional[datetime] = None

class Order(BaseModel):
    id: Optional[str] = None
    user_id: int
    symbol: str
    side: OrderSide
    order_type: OrderType = OrderType.LIMIT
    quantity: Decimal
    price: Decimal
    filled_quantity: Decimal = Decimal("0")
    remaining_quantity: Optional[Decimal] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Execution(BaseModel):
    id: Optional[str] = None
    order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    buyer_id: int
    seller_id: int
    executed_at: Optional[datetime] = None

class OrderBook(BaseModel):
    symbol: str
    bids: List[tuple[Decimal, Decimal]]  # [(price, quantity)]
    asks: List[tuple[Decimal, Decimal]]  # [(price, quantity)]
    timestamp: datetime

class Candlestick(BaseModel):
    symbol: str
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    timestamp: datetime
    interval: str  # "1m", "1h", "1d"