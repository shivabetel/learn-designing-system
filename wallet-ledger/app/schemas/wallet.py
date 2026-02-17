from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.wallet_account import AccountStatus, AccountType


class WalletRequestBase(BaseModel):
    user_id: str
    account_type: AccountType


class CreateWalletRequest(WalletRequestBase):
    pass


class WalletResponse(WalletRequestBase):
    id: UUID
    status: AccountStatus
    cached_balance: int
    created_at: datetime
    class Config:
        from_attributes = True

class BalanceResponse(BaseModel):
    account_id: UUID
    balance: int
