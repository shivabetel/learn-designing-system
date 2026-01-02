from sqlalchemy import BigInteger, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models import TimestampMixin
from app.db.base import Base
class FlashSaleProduct(Base, TimestampMixin):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    flash_sale_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("flashsale.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product.id", ondelete="CASCADE"), nullable=False)
    total_stock: Mapped[int] = mapped_column(Integer, nullable=False)