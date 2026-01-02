from sqlalchemy.ext.asyncio.session import AsyncSession


import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.core.config import settings
from app.db.base import Base
from redis.asyncio import Redis
from app.models import Movie, Show, ShowStatus, Theatre, Screen, Seat, ShowSeat, SeatType, ShowSeatStatus


@pytest.fixture
async def db_engine():
    """Create a database engine for the tests.
    
    Function-scoped to ensure it's created in the same event loop as the test.
    """
    test_db_url = settings.DATABASE_URL.replace("movie_db", "movie_db_test")
    engine = create_async_engine(
        test_db_url, 
        echo=False, 
        future=True,
        pool_size=20,
        max_overflow=10
    )

    # create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Clean slate
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup: drop tables and dispose engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create a database session for the tests."""
    async_session = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def db_session_factory(db_engine):
    """Factory to create multiple sessions for concurrent tests."""
    return async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False
    )


@pytest.fixture
async def redis_client():
    """Create a Redis client for the tests."""
    redis = Redis.from_url(
        settings.REDIS_URL,
        decode_responses=False,
        socket_connect_timeout=2
    )
    try:
        await redis.ping()
        # Clean up any existing locks from previous test runs
        keys = await redis.keys("lock:*")
        if keys:
            await redis.delete(*keys)
        yield redis
    finally:
        # Clean up locks after test
        keys = await redis.keys("lock:*")
        if keys:
            await redis.delete(*keys)
        await redis.aclose()


@pytest.fixture
async def seeded_test_data(db_engine):
    """Seed test data and return show_id and show_seat_ids for testing."""
    async_session = async_sessionmaker[AsyncSession](bind=db_engine, expire_on_commit=False)
    
    async with async_session() as session:
        # Create Theatre
        theatre = Theatre(
            name="Test Theatre",
            city="Test City",
            address="Test Address",
        )
        session.add(theatre)
        await session.flush()

        # Create Screen
        screen = Screen(
            name="Screen 1",
            theatre_id=theatre.id,
            total_seats=10,
        )
        session.add(screen)
        await session.flush()

        # Create Seats (10 seats in 2 rows)
        seats = []
        for row in ["A", "B"]:
            for num in range(1, 6):
                seat = Seat(
                    screen_id=screen.id,
                    row_label=row,
                    seat_number=num,
                    seat_type=SeatType.REGULAR,
                )
                seats.append(seat)
                session.add(seat)
        await session.flush()

        # Create Movie
        movie = Movie(
            title="Test Movie",
            description="A test movie for testing",
            duration_mins=120,
            language="English",
            certificate="U",
        )
        session.add(movie)
        await session.flush()

        # Create Show
        now = datetime.now(timezone.utc)
        show = Show(
            movie_id=movie.id,
            screen_id=screen.id,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=3),
            status=ShowStatus.SCHEDULED,
            base_price=100.00,
        )
        session.add(show)
        await session.flush()

        # Create ShowSeats for the show
        show_seats = []
        for seat in seats:
            show_seat = ShowSeat(
                show_id=show.id,
                seat_id=seat.id,
                status=ShowSeatStatus.AVAILABLE,
                price=100.00,
                version=1,
            )
            session.add(show_seat)
            show_seats.append(show_seat)
        await session.flush()
        await session.commit()

        # Return the IDs needed for testing
        show_seat_ids = [ss.id for ss in show_seats[:3]]  # First 3 seats
        
        yield {
            "show_id": show.id,
            "show_seat_ids": show_seat_ids,
            "all_show_seat_ids": [ss.id for ss in show_seats],
        }
