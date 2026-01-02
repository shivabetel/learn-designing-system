from collections import defaultdict
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select
from app.models import Movie
from app.models.Seat import Seat, ShowSeat, ShowSeatStatus
from app.models.Show import Show
from app.models.Theatre import Screen
from app.schemas.show import ShowCreate, ShowUpdate
from redis.asyncio import Redis


class CRUDShow:
    async def getShowsByMovieIdAndScreenId(self, db: AsyncSession, movie_id: int, screen_id: int):
        result = await db.execute(select(Show).where(
            Show.movie_id == movie_id,
            Show.screen_id == screen_id
        ))
        return result.scalars().all()

    async def create_show(self, db: AsyncSession, movie_id: int, screen_id: int, data: ShowCreate):
        if data.start_time >= data.end_time:
            raise ValueError("Start time must be before end time")
        if data.base_price <= 0:
            raise ValueError("Base price must be greater than 0")

        moview_result = await db.execute(select(Movie).where(Movie.id == movie_id))
        movie = moview_result.scalar_one_or_none()
        if movie is None:
            raise ValueError("Movie not found")
        screen_result = await db.execute(
            select(Screen).where(Screen.id == screen_id))
        screen = screen_result.scalar_one_or_none()
        if screen is None:
            raise ValueError("Screen not found")
        newShow = Show(**data.model_dump(),
                       movie_id=movie_id, screen_id=screen_id)
        db.add(newShow)
        await db.commit()
        await db.refresh(newShow)
        return newShow

    async def update_show(self, db: AsyncSession, movie_id: int, screen_id: int, show_id: int, data: ShowUpdate):
        result = await db.execute(select(Show).where(
            Show.movie_id == movie_id,
            Show.screen_id == screen_id,
            Show.id == show_id
        ))
        show = result.scalar_one_or_none()
        if show is None:
            return None
        for field, value in data.model_dump().items():
            if value is not None:
                setattr(show, field, value)
        await db.commit()
        await db.refresh(show)
        return show

    async def get_show_seat_layout(self, db: AsyncSession, show_id: int, redis: Redis):
        # check if the seat layout is cached
        cached_layout = await redis.get(f"seat_layout:show:{show_id}")
        if cached_layout:
            return json.loads(cached_layout)

        stmt = (select(
            ShowSeat.id.label("show_seat_id"),
            Seat.row_label,
            Seat.seat_number,
            Seat.seat_type,
            ShowSeat.status.label("db_status"),
            ShowSeat.price
        )
            .join(Seat, ShowSeat.seat_id == Seat.id)
            .join(Show, ShowSeat.show_id == Show.id)
            .where(ShowSeat.show_id == show_id))
        result = await db.execute(stmt)
        db_results = result.mappings().all()
        # get all the seat ids that are locked
        locked = await redis.smembers(f"lock:show:{show_id}:seats")
        # set comprehension to convert the list to a set
        locked_ids = {int(id) for id in locked}
        layout = defaultdict(lambda: {
            "row": None,
            "seat_type": None,
            "seats": []
        })

        for seat in db_results:
            if seat.get("db_status") == ShowSeatStatus.BOOKED:
                status = "BOOKED"
            elif seat.get("show_seat_id") in locked_ids:
                status = "LOCKED"
            else:
                status = seat.get("db_status")

            row_label = seat.get("row_label")

            layout[row_label]["row"] = row_label
            layout[row_label]["seat_type"] = seat.get("seat_type")
            layout[row_label]["seats"].append({
                "id": seat.get("show_seat_id"),
                "seat_number": seat.get("seat_number"),
                "seat_type": seat.get("seat_type"),
                "status": status,
                "price": float(seat.get("price"))
            })

        seat_layout_by_show_id = {
            "show_id": show_id,
            "layout": list(layout.values())
        }
        # cache the seat layout for 10 seconds. are we allowed to cache?
        await redis.set(f"seat_layout:show:{show_id}", json.dumps(seat_layout_by_show_id), ex=10)
        return seat_layout_by_show_id


crud_show = CRUDShow()
