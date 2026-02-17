from datetime import datetime, timezone
from enum import Enum, unique
import uuid
from sqlalchemy import BigInteger, DateTime, ForeignKey, Enum as SAEnum, String
from sqlalchemy.orm import mapped_column
from app.db.base import Base
from sqlalchemy.dialects.postgresql import UUID


class TransactionType(str, Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"
    TRANSFER = "TRANSFER"
    REFUND = "REFUND"


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Transaction(Base):
    __tablename__ = "transactions"
    id = mapped_column(UUID(as_uuid=True),
                       primary_key=True, default=uuid.uuid4)
    source_account_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallet_accounts.id"), nullable=False)
    destination_account_id = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallet_accounts.id"), nullable=False)
    transaction_type = mapped_column(SAEnum(TransactionType), nullable=False)
    idempotency_key = mapped_column(String, nullable=False, unique=True)
    amount = mapped_column(BigInteger, nullable=False)  # transaction amount
    status = mapped_column(SAEnum(TransactionStatus), nullable=False)
    created_at = mapped_column(DateTime(
        timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
