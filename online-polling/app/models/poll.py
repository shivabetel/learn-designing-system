from enum import Enum
from typing import List
from sqlalchemy import BigInteger, String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models import TimestampMixin


class PollStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Poll(Base, TimestampMixin):
    """
      this model is orm mapping object for poll table
    """
    __tablename__ = "polls"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    question: Mapped[str] = mapped_column(String(255), nullable=False)
    options: Mapped[List["Option"]] = relationship(
        back_populates="poll", cascade="all, delete-orphan")
    status: Mapped[PollStatus] = mapped_column(
        SAEnum(PollStatus), nullable=False, default=PollStatus.ACTIVE)
