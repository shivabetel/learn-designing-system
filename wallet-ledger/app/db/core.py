from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.db.base import Base
from app.models import WalletAccount, IdempotencyKey, LedgerEntry

engine = create_async_engine(settings.DATABASE_URL,
                             echo=True,
                             # Pool settings
                             pool_size=10,            # Base connections
                             max_overflow=20,         # Burst capacity
                             pool_timeout=30,         # Wait timeout
                             # Recycle every hour (prevents stale connections)
                             pool_recycle=3600,
                             # Health check (important for long-lived apps))
                             pool_pre_ping=True
                             )

async_session_factory = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=True)


async def get_db_session():
    async with async_session_factory() as session:
        yield session
        await session.rollback()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)