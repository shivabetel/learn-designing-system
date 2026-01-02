from app.db.base import Base
from app.models import TimestampMixin
from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship


class BookingSeat(Base, TimestampMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("booking.id"), nullable=False)
    show_seat_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("showseat.id"), nullable=False)
    # booking: Mapped["Booking"] = relationship(back_populates="booking_seats")
