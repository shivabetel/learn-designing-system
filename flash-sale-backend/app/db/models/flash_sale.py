from datetime import datetime
from enum import Enum
from sqlalchemy import BigInteger, DateTime, String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.models import TimestampMixin


class FlashSaleStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    ENDED = "ENDED"


class FlashSale(Base, TimestampMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False)
    status: Mapped[FlashSaleStatus] = mapped_column(
        SAEnum(FlashSaleStatus), default=FlashSaleStatus.SCHEDULED, nullable=False)
