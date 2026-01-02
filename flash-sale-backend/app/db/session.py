from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.core.config import settings
from app.db.base import Base
from app.redis import redis_client

engine = create_async_engine(
    url=settings.DATABASE_URL,
    echo=True,
    future=True

)


async_session_factory = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=True
)


async def getDB_Session():
    """
    FastAPI dependency that provides an async DB session
    and ensures it's closed after the request. 
    """

    async with async_session_factory() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("created al tables")

async def preload_inventory():
    keys = await redis_client.keys("flashsale:*:stock")
    if keys:
        await redis_client.delete(*keys)
    session = async_session_factory()
    async with session.begin():
       result =  await session.execute(text("SELECT * FROM flashsaleproduct"))      
       for row in result:
           await redis_client.set(f"flashsale:{{{row.flash_sale_id}:{row.product_id}}}:stock", row.total_stock) 

