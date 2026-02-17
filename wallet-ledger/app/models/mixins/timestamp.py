from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at = mapped_column(DateTime(timezone=True),
                               default=lambda: datetime.now(timezone.utc),
                               nullable=False)
    updated_at = mapped_column(DateTime(timezone=True),
                               default=lambda: datetime.now(timezone.utc),
                               nullable=False)
