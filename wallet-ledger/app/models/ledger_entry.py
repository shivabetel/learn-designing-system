from datetime import datetime, timezone
from enum import Enum
import uuid
from sqlalchemy import BigInteger, ForeignKey, String, Enum as SAEnum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class EntryType(str, Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"



class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(
        "wallet_accounts.id"), nullable=False)
    amount = mapped_column(BigInteger, nullable=False)
    transaction_id = mapped_column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    # the account's balance after this entry)
    running_balance = mapped_column(BigInteger, nullable=False)
    entry_type = mapped_column(SAEnum(EntryType), nullable=False)
    created_at = mapped_column(DateTime(
        timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
