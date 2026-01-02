from fastapi import APIRouter, Depends, HTTPException
from app.schemas.vote import VoteRequest, VoteResponse
from app.db.core import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.vote import crud_vote
from app.exceptions.vote_already_exists_exception import VoteAlreadyExistsException


router = APIRouter(prefix="/vote")


@router.post("/{poll_id}", response_model=VoteResponse)
async def create_vote(poll_id: int, vote: VoteRequest, db: AsyncSession = Depends(get_db_session)):
    try:
        if poll_id != vote.poll_id:
            raise HTTPException(
                status_code=400, detail="Poll ID does not match")
        return await crud_vote.create_vote(db, vote)
    except VoteAlreadyExistsException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
