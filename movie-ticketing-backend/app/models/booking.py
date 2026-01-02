from enum import Enum
from typing import List
from sqlalchemy import BigInteger, Enum as SAEnum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models import TimestampMixin


class BookingStatus(str, Enum):
    INITIATED = "INITIATED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class Booking(Base, TimestampMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus), nullable=False, default=BookingStatus.INITIATED)
    show_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("show.id"), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(100), nullable=True, unique=True, index=True)
    seats: Mapped[List["BookingSeat"]] = relationship(
        cascade="all, delete-orphan")
