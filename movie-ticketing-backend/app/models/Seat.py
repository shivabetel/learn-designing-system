from enum import Enum
from typing import Optional
from sqlalchemy import BigInteger, Float, ForeignKey, Integer, Numeric, String, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.db.base import Base
from app.models import TimestampMixin


class SeatType(str, Enum):
    REGULAR = "REGULAR"
    PREMIUM = "PREMIUM"
    RECLINER = "RECLINER"


class ShowSeatStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    LOCKED = "LOCKED"
    UNAVAILABLE = "UNAVAILABLE"  # e.g., broken seat


class Seat(Base, TimestampMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    row_label: Mapped[str] = mapped_column(String(5), nullable=False)
    seat_type: Mapped[SeatType] = mapped_column(SAEnum(
        SeatType, name="seat_type_enum"), nullable=False, default=SeatType.REGULAR)
    screen_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("screen.id", ondelete="CASCADE"), index=True, nullable=False)
    screen: Mapped["Screen"] = relationship(
        back_populates="seats")
    show_seats: Mapped[list["ShowSeat"]] = relationship(back_populates="seat", cascade="all, delete-orphan")



class ShowSeat(Base, TimestampMixin):
    __table_args__ = (
        UniqueConstraint("show_id", "seat_id", name="uix_show_seat_unique"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    show_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(
        "show.id", ondelete="CASCADE"), nullable=False)
    seat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(
        "seat.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[ShowSeatStatus] = mapped_column(SAEnum(
        ShowSeatStatus), nullable=False, default=ShowSeatStatus.AVAILABLE)
    price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    show: Mapped["Show"] = relationship(back_populates="show_seats")
    seat: Mapped["Seat"] = relationship(back_populates="show_seats")