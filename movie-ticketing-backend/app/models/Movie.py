from enum import Enum
from typing import Optional
from sqlalchemy import BigInteger, Integer, String, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models import TimestampMixin


class Certificate(str, Enum):
    U = "U"
    UA = "UA"
    A = "A"
    S = "S"


class Movie(Base, TimestampMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    duration_mins: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    certificate: Mapped[Optional[Certificate]] = mapped_column(
        SAEnum(Certificate, name="certificate_enum"), nullable=False)
    # genre: Mapped[list[str]] = mapped_column(ARRAY(String(50)), nullable=False)
    shows: Mapped[list["Show"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan")
