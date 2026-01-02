from typing import AsyncGenerator
from app.core.config import get_settings;
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base;


settings = get_settings();

engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=True,
    future=True
)

async_session = async_sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)


async def getDB_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async DB session
    and ensures it's closed after the request.
    """
    async with async_session() as session:
        yield session


async def init_db() -> None:
    """
    TEMP: Create all tables based on models.
    We will replace this with Alembic migrations later.
    """
    async with engine.begin() as conn:
         # Drop all tables to recreate with updated enums
        # await conn.run_sync(Base.metadata.drop_all)
        # print("Dropped all tables")
        await conn.run_sync(Base.metadata.create_all)
        print("Created all tables")