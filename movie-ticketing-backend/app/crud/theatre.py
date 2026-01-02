from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import insert, select
from app.models.Theatre import Theatre
from app.schemas.theatre import TheatreBase, TheatreCreate, TheatreUpdate


class TheatreCreationError(Exception):
    pass


class CRUDTheatre:
    async def get_theatre(self, db: AsyncSession, theatre_id: int) -> Theatre | None:
        result = await db.execute(select(Theatre)
                                  .where(Theatre.id == theatre_id)
                                  .options(selectinload(Theatre.screens))
                                  )
        return result.scalar_one_or_none()

    async def create_theatre(self, db: AsyncSession, data: TheatreCreate):
        try:
            theatre = Theatre(**data.model_dump())
            db.add(theatre)
            await db.commit()
            await db.refresh(theatre)
            # Eagerly load screens after refresh
            await db.refresh(theatre, ['screens'])
            return theatre
        except Exception as e:
            print(e)
            raise TheatreCreationError(f"Error creating theatre: {e}")

    async def get_all_theatres(self, db: AsyncSession):
        result = await db.execute(
            select(Theatre)
            .options(selectinload(Theatre.screens))
        )
        return result.scalars().all()

    async def update_theatre(self, db: AsyncSession, theatre_id: int, data: TheatreUpdate):
        result = await db.execute(select(Theatre)
                                  .where(Theatre.id == theatre_id)
                                  .options(selectinload(Theatre.screens)))
        theatre = result.scalar_one_or_none()
        if theatre is None:
            return None
        for field, value in data.model_dump().items:
            setattr(theatre, field, value)
        await db.commit()
        await db.refresh(theatre)
        # Refresh screens after refresh
        await db.refresh(theatre, ['screens'])
        return theatre


crud_theatre = CRUDTheatre()
