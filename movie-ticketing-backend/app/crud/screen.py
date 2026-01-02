from sqlalchemy.engine.result import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select
from app.models.Theatre import Screen
from app.schemas.screen import ScreenCreate


class ScreenCreationError(Exception):
    pass


class CRUDScreen:
    async def get_screen(self, db: AsyncSession, screen_id: int):
        result: Result = await db.execute(select(Screen)
                                          .where(Screen.id == screen_id))
        return result.scalar_one_or_none()

    async def create_screen_by_theatre_id(self, db: AsyncSession, theatre_id: int, data: ScreenCreate):
        try:
            screen = Screen(
                theatre_id=theatre_id,
                **data.model_dump()
            )  # Create a new screen object
            db.add(screen)
            await db.commit()
            db.refresh(screen)
            return screen
        except Exception as e:
            print(e)
            raise ScreenCreationError(f"Error creating screen: {e}")

    async def get_all_screens(self, db: AsyncSession):
        result = await db.execute(select(Screen))
        return result.scalars().all()

    async def getScreenByTheatreId(self, db: AsyncSession, theatre_id: int):
        result = await db.execute(select(Screen)
                                  .where(Screen.theatre_id == theatre_id))
        return result.scalars().all()


crud_screen = CRUDScreen()
