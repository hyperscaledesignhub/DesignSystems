from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from decimal import Decimal

class BaseEntity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class User(BaseEntity):
    email: str
    password_hash: str
    full_name: str
    status: str = "active"

class Wallet(BaseEntity):
    user_id: UUID
    balance: Decimal = Decimal("0.00")
    currency: str = "USD"
    status: str = "active"

class Transaction(BaseEntity):
    from_wallet_id: Optional[UUID] = None
    to_wallet_id: Optional[UUID] = None
    amount: Decimal
    currency: str
    status: str = "pending"
    transaction_type: str
    idempotency_key: UUID
    completed_at: Optional[datetime] = None

class Event(BaseEntity):
    event_type: str
    wallet_id: UUID
    amount: Decimal
    currency: str
    transaction_id: UUID
    metadata: dict = {}

class TransferRequest(BaseModel):
    from_wallet_id: UUID
    to_wallet_id: UUID
    amount: Decimal
    currency: str = "USD"
    idempotency_key: UUID

class UserRegistration(BaseModel):
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class WalletCreation(BaseModel):
    user_id: UUID
    currency: str = "USD"