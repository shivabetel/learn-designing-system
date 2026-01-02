from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models import TimestampMixin


class VoteLog(Base, TimestampMixin):
    """
    This model is used to log the votes for a poll.
    """

    __tablename__ = "vote_log"
    __table_args__ = UniqueConstraint(
        "poll_id", "user_id", name="uix_poll_user_unique"), 
    vote_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    poll_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False)
    user_id: Mapped[str] = mapped_column(String(55), nullable=False)
    option_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False)
