import asyncio
from datetime import datetime, timedelta, timezone

from app.db.session import async_session as AsyncSessionLocal, engine
from app.models import (
    Theatre,
    Screen,
    Seat,
    SeatType,
    Movie,
    Show,
    ShowStatus,
    ShowSeat,
    ShowSeatStatus,
)


async def seed():
    async with AsyncSessionLocal() as session:

        # ------------------------------------------------------------------------------------
        # 1. Create Theatre
        # ------------------------------------------------------------------------------------
        theatre = Theatre(
            name="PVR Cinemas - Koramangala",
            city="Bangalore",
            address="Koramangala 7th Block, Near Forum Mall",
        )
        session.add(theatre)
        await session.flush()  # get theatre.id

        # ------------------------------------------------------------------------------------
        # 2. Create Screens
        # ------------------------------------------------------------------------------------
        screen1 = Screen(
            name="Screen 1",
            theatre_id=theatre.id,
            total_seats=50,
        )
        screen2 = Screen(
            name="Screen 2",
            theatre_id=theatre.id,
            total_seats=40,
        )
        session.add_all([screen1, screen2])
        await session.flush()

        # ------------------------------------------------------------------------------------
        # 3. Create Seats for Screen 1 (5 rows x 10 seats)
        # ------------------------------------------------------------------------------------
        seats_screen1 = []
        for row in ["A", "B", "C", "D", "E"]:
            for num in range(1, 11):
                seat_type = (
                    SeatType.RECLINER if row == "A" else
                    SeatType.PREMIUM if row in ["B", "C"] else
                    SeatType.REGULAR
                )
                seats_screen1.append(
                    Seat(
                        screen_id=screen1.id,
                        row_label=row,
                        seat_number=num,
                        seat_type=seat_type,
                    )
                )

        session.add_all(seats_screen1)
        await session.flush()

        # ------------------------------------------------------------------------------------
        # 4. Create Movies
        # ------------------------------------------------------------------------------------
        movie1 = Movie(
            title="Interstellar",
            description="A group of explorers travel through a wormhole in space.",
            duration_mins=169,
            language="English",
            certificate="UA",
        )

        movie2 = Movie(
            title="KGF Chapter 2",
            description="Rocky rises again.",
            duration_mins=168,
            language="Kannada",
            certificate="UA",
        )

        session.add_all([movie1, movie2])
        await session.flush()

        # ------------------------------------------------------------------------------------
        # 5. Create Shows (Today's date)
        # ------------------------------------------------------------------------------------
        now = datetime.now(timezone.utc)

        show1 = Show(
            movie_id=movie1.id,
            screen_id=screen1.id,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=1, minutes=169),
            status=ShowStatus.SCHEDULED,
            base_price=300.00,
        )

        show2 = Show(
            movie_id=movie1.id,
            screen_id=screen1.id,
            start_time=now + timedelta(hours=4),
            end_time=now + timedelta(hours=4, minutes=169),
            status=ShowStatus.SCHEDULED,
            base_price=350.00,  # Different show, different base price
        )

        show3 = Show(
            movie_id=movie2.id,
            screen_id=screen2.id,
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=2, minutes=168),
            status=ShowStatus.SCHEDULED,
            base_price=250.00,
        )

        session.add_all([show1, show2, show3])
        await session.flush()

        # ------------------------------------------------------------------------------------
        # 6. Create ShowSeat entries for each show
        # ------------------------------------------------------------------------------------
        async def create_show_seats_for_show(show, seats):
            show_seats = []
            for seat in seats:
                show_seats.append(
                    ShowSeat(
                        show_id=show.id,
                        seat_id=seat.id,
                        status=ShowSeatStatus.AVAILABLE,
                        price=show.base_price,  # or dynamic override
                        version=1,
                    )
                )
            session.add_all(show_seats)

        await create_show_seats_for_show(show1, seats_screen1)
        await create_show_seats_for_show(show2, seats_screen1)
        await create_show_seats_for_show(show3, seats_screen1)

        # ------------------------------------------------------------------------------------
        # 7. Commit everything
        # ------------------------------------------------------------------------------------
        await session.commit()
        print("🎉 Test data seeded successfully!")


async def main():
    async with engine.begin() as conn:
        # Ensure tables exist (for dev only)
        await conn.run_sync(lambda _: None)
    await seed()


if __name__ == "__main__":
    asyncio.run(main())
