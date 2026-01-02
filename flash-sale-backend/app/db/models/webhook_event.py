from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.models import TimestampMixin


class WebhookEvent(Base, TimestampMixin):
    """
    Tracks processed webhook events for idempotency.
    If event_id exists, webhook was already processed.
    """
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=True)

