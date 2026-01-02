from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.core import get_db_session
from app.crud.poll import crud_poll
from app.schemas.poll import (
    PollCreate,
    PollResponse,
    PollListResponse,
    PollResultsResponse,
    OptionResponse
)
from app.schemas.vote import VoteRequest, VoteResponse
from app.exceptions.vote_already_exists_exception import VoteAlreadyExistsException

router = APIRouter(prefix="/poll")


@router.get("", response_model=List[PollListResponse])
async def list_polls(db: AsyncSession = Depends(get_db_session)):
    """Get all polls with summary information."""
    return await crud_poll.get_all_polls(db)


@router.get("/{poll_id}", response_model=PollResponse)
async def get_poll(poll_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get a single poll with its options."""
    poll = await crud_poll.get_poll_by_id(db, poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    return PollResponse(
        id=poll.id,
        question=poll.question,
        status=poll.status.value,
        options=[OptionResponse(id=opt.id, text=opt.text)
                 for opt in poll.options],
        created_at=poll.created_at
    )


@router.post("", response_model=PollResponse, status_code=201)
async def create_poll(poll_data: PollCreate, db: AsyncSession = Depends(get_db_session)):
    """Create a new poll with options."""
    if len(poll_data.options) < 2:
        raise HTTPException(
            status_code=400,
            detail="A poll must have at least 2 options"
        )

    poll = await crud_poll.create_poll(db, poll_data)

    return PollResponse(
        id=poll.id,
        question=poll.question,
        status=poll.status.value,
        options=[OptionResponse(id=opt.id, text=opt.text)
                 for opt in poll.options],
        created_at=poll.created_at
    )


@router.get("/{poll_id}/results", response_model=PollResultsResponse)
async def get_poll_results(poll_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get poll results with vote counts."""
    results = await crud_poll.get_poll_results(db, poll_id)
    if not results:
        raise HTTPException(status_code=404, detail="Poll not found")
    return results


@router.get("/{poll_id}/check-vote/{user_id}")
async def check_user_vote(
    poll_id: int,
    user_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Check if a user has already voted on a poll."""
    has_voted = await crud_poll.check_user_voted(db, poll_id, user_id)
    return {"poll_id": poll_id, "user_id": user_id, "has_voted": has_voted}


@router.post("/{poll_id}/vote", response_model=VoteResponse)
async def vote_poll(poll_id: int, vote: VoteRequest, db: AsyncSession = Depends(get_db_session)):
    try:
        if poll_id != vote.poll_id:
            raise HTTPException(
                status_code=400, detail="Poll ID does not match")
        return await crud_poll.vote_poll(db, poll_id, vote)
    except VoteAlreadyExistsException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
