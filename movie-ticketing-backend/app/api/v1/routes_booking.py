from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.idempotency import check_idempotency
from app.crud.booking import crud_booking
from app.db.session import getDB_session
from app.exceptions import seat_already_locked
from app.exceptions.booking_not_found import BookingNotFoundException
from app.exceptions.seat_already_locked import SeatAlreadyLockedException
from app.redis import get_redis

router = APIRouter(
    prefix="/booking"
)


class LockSeatPayload(BaseModel):
    show_seat_ids: List[int]


@router.post("/seats/{show_id}/lock")
async def lock_seats(
        show_id: int,
        data: LockSeatPayload,
        db: AsyncSession = Depends(getDB_session),
        redis: Redis = Depends(get_redis)):
    try:
        return await crud_booking.lock_seats(db, redis, show_id, data.show_seat_ids)
    except SeatAlreadyLockedException as seat_already_locked:
        raise HTTPException(400, str(seat_already_locked))
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/booking/{booking_id}/confirm")
async def confirm_booking(
        booking_id: int,
        request: Request,
        db: AsyncSession = Depends(getDB_session),
        redis: Redis = Depends(get_redis)):
    try:
        idem_key, cached, is_repeat = await check_idempotency(request, redis)
        if is_repeat:
            return cached
        return await crud_booking.confirmBooking(db, booking_id, idem_key, redis)
    except BookingNotFoundException as booking_not_found:
        raise HTTPException(400, str(booking_not_found))
    except Exception as e:
        raise HTTPException(400, str(e))
