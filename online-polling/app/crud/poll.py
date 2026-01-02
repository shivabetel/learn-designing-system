from typing import List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import text

from app.models.poll import Poll, PollStatus
from app.models.option import Option
from app.models.vote_log import VoteLog
from app.schemas.poll import PollCreate, PollListResponse, PollResultsResponse, OptionWithVotes
from app.exceptions.vote_already_exists_exception import VoteAlreadyExistsException
from app.schemas.vote import VoteRequest

INSERT_VOTE_LOG_SQL = """
INSERT INTO vote_log (poll_id, option_id, user_id, created_at, updated_at) VALUES (:poll_id, :option_id, :user_id, NOW(), NOW())
ON CONFLICT (poll_id, user_id) DO NOTHING
"""


class CRUDPoll:
    async def get_all_polls(self, db: AsyncSession) -> List[PollListResponse]:
        """Get all polls with vote counts."""
        # Get polls with option count and total votes
        result = await db.execute(
            select(
                Poll.id,
                Poll.question,
                Poll.status,
                Poll.created_at,
                func.count(Option.id.distinct()).label("option_count"),
                func.count(VoteLog.vote_id).label("total_votes")
            )
            .outerjoin(Option, Poll.id == Option.poll_id)
            .outerjoin(VoteLog, Poll.id == VoteLog.poll_id)
            .group_by(Poll.id)
            .order_by(Poll.created_at.desc())
        )

        polls = []
        for row in result:
            polls.append(PollListResponse(
                id=row.id,
                question=row.question,
                status=row.status.value,
                option_count=row.option_count,
                total_votes=row.total_votes,
                created_at=row.created_at
            ))
        return polls

    async def get_poll_by_id(self, db: AsyncSession, poll_id: int) -> Poll | None:
        """Get a single poll with its options."""
        result = await db.execute(
            select(Poll)
            .options(selectinload(Poll.options))
            .where(Poll.id == poll_id)
        )
        return result.scalar_one_or_none()

    async def create_poll(self, db: AsyncSession, poll_data: PollCreate) -> Poll:
        """Create a new poll with options."""
        poll = Poll(
            question=poll_data.question,
            status=PollStatus.ACTIVE
        )
        db.add(poll)
        await db.flush()  # Get the poll ID

        for option_text in poll_data.options:
            option = Option(text=option_text, poll_id=poll.id)
            db.add(option)

        await db.commit()
        await db.refresh(poll)

        # Load options relationship
        result = await db.execute(
            select(Poll)
            .options(selectinload(Poll.options))
            .where(Poll.id == poll.id)
        )
        return result.scalar_one()

    async def get_poll_results(self, db: AsyncSession, poll_id: int) -> PollResultsResponse | None:
        """Get poll results with vote counts per option."""
        # First check if poll exists
        poll = await self.get_poll_by_id(db, poll_id)
        if not poll:
            return None

        # Get vote counts per option
        result = await db.execute(
            select(
                Option.id,
                Option.text,
                func.count(VoteLog.vote_id).label("vote_count")
            )
            .outerjoin(VoteLog, Option.id == VoteLog.option_id)
            .where(Option.poll_id == poll_id)
            .group_by(Option.id)
        )

        options_with_votes = []
        total_votes = 0

        rows = result.all()
        for row in rows:
            total_votes += row.vote_count

        for row in rows:
            percentage = (row.vote_count / total_votes *
                          100) if total_votes > 0 else 0
            options_with_votes.append(OptionWithVotes(
                id=row.id,
                text=row.text,
                vote_count=row.vote_count,
                percentage=round(percentage, 1)
            ))

        # Sort by vote count descending
        options_with_votes.sort(key=lambda x: x.vote_count, reverse=True)

        return PollResultsResponse(
            id=poll.id,
            question=poll.question,
            total_votes=total_votes,
            options=options_with_votes
        )

    async def check_user_voted(self, db: AsyncSession, poll_id: int, user_id: str) -> bool:
        """Check if a user has already voted on a poll."""
        result = await db.execute(
            select(VoteLog)
            .where(VoteLog.poll_id == poll_id)
            .where(VoteLog.user_id == user_id)
        )
        return result.scalar_one_or_none() is not None

    async def vote_poll(self, db: AsyncSession, poll_id: int, vote_request: VoteRequest):
        """Vote on a poll."""
        result = await db.execute(
            text(INSERT_VOTE_LOG_SQL),
            {
                "poll_id": poll_id,
                "option_id": vote_request.option_id,
                "user_id": vote_request.user_id,
            }
        )
        await db.commit()
        
        if result.rowcount == 0:
            raise VoteAlreadyExistsException(
                f"Vote already exists for poll {poll_id} and user {vote_request.user_id}"
            )
        
        return {"message": "Vote recorded successfully", "success": True}


crud_poll = CRUDPoll()
