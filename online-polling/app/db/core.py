from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
from app.db.base import Base
engine = create_async_engine(
    url=settings.DB_URL,
    echo=True,
    future=True
)
async_session_factory = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=True
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
        await session.rollback()


async def init_db():
    """
    This function is used to initialize the database.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("created all tables")