from fastapi import APIRouter, Depends, HTTPException
from app.crud.movie import crud_movie
from app.db.session import getDB_session
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.movie import MovieCreate, MovieResponse, MovieUpdate

router = APIRouter(
    prefix="/movie"
)


@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(movie_id: int, db: AsyncSession = Depends(getDB_session)):
    result = await crud_movie.get_movie(db, movie_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return result


@router.post("/", response_model=MovieResponse)
async def create_movie(movie: MovieCreate, db: AsyncSession = Depends(getDB_session)):
    return await crud_movie.create_movie(db, movie)


@router.put("/{movie_id}", response_model=MovieResponse)
async def update_movie(movie_id: int, movie: MovieUpdate, db: AsyncSession = Depends(getDB_session)):
    result = await crud_movie.update_movie(db=db, movie_id=movie_id, data=movie)
    if result is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return result
