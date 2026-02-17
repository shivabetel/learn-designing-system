from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, Field
from app.models.transaction import TransactionStatus, TransactionType


class TransactionBase(BaseModel):
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: int = Field(gt=0)


class CreditRequest(BaseModel):
    amount: int = Field(gt=0)
    metadata: Optional[dict] = None


class DebitRequest(BaseModel):
    amount: int = Field(gt=0)
    metadata: Optional[dict] = None


class TransferRequest(BaseModel):
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: int = Field(gt=0)
    metadata: Optional[dict] = None


class TransactionResponse(BaseModel):
    id: uuid.UUID
    transaction_type: TransactionType
    status: TransactionStatus
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: int
    created_at: datetime
    class Config:
        from_attributes = True