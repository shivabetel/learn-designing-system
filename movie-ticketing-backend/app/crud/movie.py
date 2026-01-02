from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select

from app.models.Movie import Movie
from app.schemas.movie import MovieCreate, MovieUpdate


class CRUDMovie:
    async def get_movie(self, db: AsyncSession, movie_id: int):
        result = await db.execute(select(Movie).where(Movie.id == movie_id))
        return result.scalar_one_or_none()

    async def create_movie(self, db: AsyncSession, data: MovieCreate):
        movie = Movie(**data.model_dump())
        db.add(movie)
        await db.commit()
        await db.refresh(movie)
        return movie

    async def update_movie(self, db: AsyncSession, movie_id: int, data: MovieUpdate):
        result = await db.execute(select(Movie).where(Movie.id == movie_id))
        movie = result.scalar_one_or_none()
        if movie is None:
            return None
        for field, value in data.model_dump().items():
            setattr(movie, field, value)
        await db.commit()
        await db.refresh(movie)
        return movie


crud_movie = CRUDMovie()
