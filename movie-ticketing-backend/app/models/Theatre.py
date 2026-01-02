from sqlalchemy import BigInteger, ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship;
from app.db.base import Base;
from app.models import TimestampMixin

class Theatre(Base, TimestampMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    screens: Mapped[list["Screen"]] = relationship(cascade="all, delete-orphan")



class Screen(Base, TimestampMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    theatre_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("theatre.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    seats: Mapped[list["Seat"]] = relationship(back_populates="screen", cascade="all, delete-orphan")
    shows: Mapped[list["Show"]] = relationship(back_populates="screen", cascade="all, delete-orphan")