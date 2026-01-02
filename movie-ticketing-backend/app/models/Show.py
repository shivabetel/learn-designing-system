from enum import Enum
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models import TimestampMixin
from datetime import datetime



class ShowStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class Show(Base, TimestampMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    movie_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(
        "movie.id", ondelete="CASCADE"), nullable=False)
    screen_id: Mapped[int] = mapped_column(BigInteger, ForeignKey(
        "screen.id", ondelete="CASCADE"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    base_price: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[ShowStatus] = mapped_column(
        SAEnum(ShowStatus), nullable=False)
    movie: Mapped["Movie"] = relationship(back_populates="shows")
    screen: Mapped["Screen"] = relationship(back_populates="shows")
    show_seats: Mapped[list["ShowSeat"]] = relationship(back_populates="show", cascade="all, delete-orphan")
    # screen: Mapped["Screen"] = relationship(back_populates="shows", cascade="all, delete-orphan")