from enum import Enum
from sqlalchemy import BigInteger, String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from  app.db.base import Base
from app.db.models import TimestampMixin


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PAYMENT_IN_PROGRESS = "PAYMENT_IN_PROGRESS"
    CONFIRMED = "CONFIRMED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class Order(Base, TimestampMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False)
    flash_sale_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
