import pytest
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.base import Base
from redis.asyncio import Redis


@pytest.fixture
async def db_engine():
    database_url = settings.DATABASE_URL.replace(
        "inventory_db", "inventory_db_test")
    engine = create_async_engine(
        url=database_url,
        echo=False,
        future=True,
        pool_size=20,
        max_overflow=10
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    async_session_factory = async_sessionmaker(
        bind=db_engine,
        autoflush=False,
        expire_on_commit=False
    )


@pytest.fixture
async def redis_client():
    redis = Redis.from_url(
        settings.REDIS_URL,
        decode_responses=False,
        socket_connect_timeout=2)

    yield redis
    await redis.aclose()

