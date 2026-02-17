from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from sqlalchemy.dialects.postgresql import JSONB

from .mixins.timestamp import TimestampMixin 
class IdempotencyKey(Base, TimestampMixin):
    __tablename__ = "idempotency_keys"
    key: Mapped[str] =  mapped_column(String, primary_key=True)
    request_hash: Mapped[str] =  mapped_column(String, nullable=False)
    request_json: Mapped[dict] = mapped_column(JSONB, nullable=False)