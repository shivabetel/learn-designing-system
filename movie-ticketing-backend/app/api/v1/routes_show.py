from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException
from app.crud.show import crud_show
from app.db.session import getDB_session
from app.redis import get_redis
from app.schemas.show import ShowCreate, ShowResponse, ShowUpdate


router = APIRouter(
    prefix="/show"
)


@router.get("/{show_id}/seat-layout")
async def get_show_seat_layout(
        show_id: int,
        db: AsyncSession = Depends(getDB_session),
        redis: Redis = Depends(get_redis)):
    return await crud_show.get_show_seat_layout(db, show_id, redis)


@router.get("/{movie_id}/{screen_id}", response_model=list[ShowResponse])
async def get_shows_by_movie_id_and_screen_id(movie_id: int, screen_id: int, db: AsyncSession = Depends(getDB_session)):
    return await crud_show.getShowsByMovieIdAndScreenId(db, movie_id, screen_id)


@router.post("/{movie_id}/{screen_id}", response_model=ShowResponse)
async def create_show(movie_id: int, screen_id: int, show: ShowCreate, db: AsyncSession = Depends(getDB_session)):
    try:
        return await crud_show.create_show(db, movie_id, screen_id, show)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{movie_id}/{screen_id}/{show_id}", response_model=ShowResponse)
async def update_show(movie_id: int, screen_id: int, show_id: int, show: ShowUpdate, db: AsyncSession = Depends(getDB_session)):
    try:
        return await crud_show.update_show(db, movie_id, screen_id, show_id, show)
    # except ValueError as e:
    #     raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
