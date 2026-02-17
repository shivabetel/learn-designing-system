from enum import Enum
import uuid
from sqlalchemy import BigInteger, String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from .mixins.timestamp import TimestampMixin 

class AccountType(str, Enum):
    USER_ACCOUNT = "USER_ACCOUNT"
    MERCHANT_ACCOUNT = "MERCHANT_ACCOUNT"
    SYSTEM = "SYSTEM"
class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"    
class WalletAccount(Base, TimestampMixin):
    __tablename__ = "wallet_accounts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    account_type: Mapped[AccountType] = mapped_column(SAEnum(AccountType), default=AccountType.USER_ACCOUNT, nullable=False)
    status: Mapped[AccountStatus] = mapped_column(SAEnum(AccountStatus), default=AccountStatus.ACTIVE, nullable=False)
    cached_balance: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    version: Mapped[int] = mapped_column(default=0, nullable=False)