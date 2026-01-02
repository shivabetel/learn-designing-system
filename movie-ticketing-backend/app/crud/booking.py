import json
from redis.asyncio import Redis
from typing import List

from sqlalchemy.engine import interfaces
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select

from app.core.idempotency import check_idempotency
from app.exceptions.booking_not_found import BookingNotFoundException
from app.exceptions.seat_already_locked import SeatAlreadyLockedException
from app.exceptions.show_seat_not_found import ShowSeatNotFoundException
from app.models.Seat import ShowSeat, ShowSeatStatus
from app.models.booking import Booking, BookingStatus
from app.models.booking_seat import BookingSeat
from app.schemas.booking import BookingResponse


# this script is cluster-safe, as it uses hash tags to ensure all keys for a show go to the same slot
# key = "prefix:{tag}:suffix"
#               ↑
#         Only {tag} part is hashed
LOCK_MULTIPLE_SEATS_SCRIPT_CLUSTER_SAFE = """
-- KEYS[1] = set_key pattern base (not used in cluster-safe version)
-- ARGV[1] = booking_id
-- ARGV[2] = ttl (600)
-- ARGV[3] = show_id
-- ARGV[4..N] = seat_ids to lock

local booking_id = ARGV[1]
local ttl = tonumber(ARGV[2])
local show_id = ARGV[3]

-- Hash tag ensures all keys for this show go to the same slot
local key_prefix = "lock:{show:" .. show_id .. "}"

-- Step 1: Check ALL seats first (atomic check)
for i = 4, #ARGV do
    local seat_id = ARGV[i]
    local lock_key = key_prefix .. ":seat:" .. seat_id
    local exists = redis.call('EXISTS', lock_key)
    if exists == 1 then
        return 0
    end
end

-- Step 2: All seats available, lock them ALL atomically
local set_key = key_prefix .. ":seats"
for i = 4, #ARGV do
    local seat_id = ARGV[i]
    local lock_key = key_prefix .. ":seat:" .. seat_id
    redis.call('SET', lock_key, booking_id, 'EX', ttl, 'NX')
    redis.call('SADD', set_key, seat_id)
end

return 1
"""

# this script is not cluster-safe, as it does not use hash tags to ensure all keys for a show go to the same slot
LOCK_MULTIPLE_SEATS_SCRIPT = """
-- KEYS[1] = set_key (e.g., "lock:show:123:seats")
-- ARGV[1] = booking_id
-- ARGV[2] = ttl (600)
-- ARGV[3] = show_id
-- ARGV[4..N] = seat_ids to lock

local set_key = KEYS[1]
local booking_id = ARGV[1]
local ttl = tonumber(ARGV[2])
local show_id = ARGV[3]

-- Step 1: Check ALL seats first (atomic check)
for i = 4, #ARGV do
    local seat_id = ARGV[i]  -- Get seat_id from arguments
    local lock_key = "lock:show:" .. show_id .. ":seat:" .. seat_id -- Example: "lock:show:123:seat:4"
    local exists = redis.call('EXISTS', lock_key)
    if exists == 1 then
        -- At least one seat is already locked, abort everything
        return 0
    end
end

-- Step 2: All seats available, lock them ALL atomically
for i = 4, #ARGV do
    local seat_id = ARGV[i]
    local lock_key = "lock:show:" .. show_id .. ":seat:" .. seat_id
    -- Set lock
    redis.call('SET', lock_key, booking_id, 'EX', ttl, 'NX')
    -- Add to set
    redis.call('SADD', set_key, seat_id)
end

return 1  -- Success
"""


class CRDBooking:
    async def lock_seats_atomic(self, redis: Redis, show_id: int, show_seat_ids: List[int], booking_id: int):
        """
        Atomically lock multiple seats - all or nothing
        """
        set_key = f"lock:show:{show_id}:seats"

        # Prepare arguments: [booking_id, ttl, show_id, ...seat_ids]
        args = [str(booking_id), "600", str(show_id)] + [str(sid)
                                                         for sid in show_seat_ids]

        result = await redis.eval(
            LOCK_MULTIPLE_SEATS_SCRIPT_CLUSTER_SAFE,
            1,  # Number of keys
            set_key,  # KEYS[1]
            *args  # ARGV[1..N]
        )
        return result == 1  # Returns True if all seats locked, False otherwise

    async def lock_seat(self, redis: Redis, show_id: int, show_seat_id: int, booking_id: int):
        key = f"lock:show:{show_id}:seat:{show_seat_id}"
        set_key = f"lock:show:{show_id}:seats"
        # nx=True means set only if the key does not exist
        success = await redis.set(key, booking_id, ex=600, nx=True)
        if success:
            await redis.sadd(set_key, show_seat_id)
        return success

   # .1 first check if the seats are available. always db is source of truth.
   # . 2 calculate the total amount.
   # . 3 create a booking.
   # . 4 lock the seats.
   # . 5 if the seats are not locked, raise an exception.
   # . 6 if exception occurs, rollback the transaction and cleanup the locks.
   # . 7 add the booking seats.
   # . 8 commit the transaction.
   # . 9 return the booking id.

    async def lock_seats(self, db: AsyncSession, redis: Redis, show_id: int, show_seat_ids: List[int]):
        show_seats_results = await db.scalars(
            select(ShowSeat)
            .where(ShowSeat.show_id == show_id)
            .where(ShowSeat.id.in_(show_seat_ids))
            .where(ShowSeat.status == ShowSeatStatus.AVAILABLE)
        )
        show_seats = show_seats_results.all()
        if len(show_seats) != len(show_seat_ids):
            raise ShowSeatNotFoundException(
                "One or more seats are not available")

        total_amount = sum([show_seat.price for show_seat in show_seats])
        booking = Booking(show_id=show_id, total_amount=total_amount)
        db.add(booking)
        await db.flush()
        # locked = []
        set_key = f"lock:show:{show_id}:seats"
        try:
            # for show_seat_id in show_seat_ids:
            #     success = await self.lock_seat(redis, show_id, show_seat_id, booking.id)
            #     if not success:
            #         # rollback
            #         for s in locked:
            #             await redis.delete(f"lock:show:{show_id}:seat:{s}")
            #             await redis.srem(set_key, s)
            #         raise SeatAlreadyLockedException(
            #             f"Seat {show_seat_id} is already locked")
            #     locked.append(show_seat_id)
            #   locked = show_seat_ids
            success = await self.lock_seats_atomic(redis, show_id, show_seat_ids, booking.id)
            if not success:
                raise SeatAlreadyLockedException(
                    "One or more seats are already locked")

            for show_seat_id in show_seat_ids:
                booking_seat = BookingSeat(
                    booking_id=booking.id, show_seat_id=show_seat_id)
                db.add(booking_seat)

            await db.commit()
            return booking.id
        except Exception:
            # for s in locked:
            #     await redis.delete(f"lock:show:{show_id}:seat:{s}")
            #     await redis.srem(set_key, s)
            # Cleanup Redis locks on any failure
            for show_seat_id in show_seat_ids:
                await redis.delete(f"lock:show:{show_id}:seat:{show_seat_id}")
                await redis.srem(set_key, show_seat_id)

            await db.rollback()
            raise

    async def confirm_booking(self, db: AsyncSession, booking_id: int, idem_key: str, redis: Redis):
        async with db.begin():
            result = await db.execute(
                select(Booking)
                .where(Booking.id == booking_id)
                .with_for_update()  # pesimistic locking
            )
            booking = result.scalar_one_or_none()
            if booking is None:
                raise BookingNotFoundException(
                    f"Booking {booking_id} not found")

            if booking.status != BookingStatus.INITIATED:
                raise ValueError(
                    f"Cannot confirm booking with status {booking.status}")
            # booking = await db.get(Booking, booking_id)
            booking_seats = await db.scalars(select(BookingSeat).where(BookingSeat.booking_id == booking_id))
            show_seat_ids = [
                booking_seat.show_seat_id for booking_seat in booking_seats]
            for show_seat_id in show_seat_ids:
                show_seat = await db.get(ShowSeat, show_seat_id)
                if show_seat is None:
                    raise ShowSeatNotFoundException(
                        f"Show seat {show_seat_id} not found")
                show_seat.status = ShowSeatStatus.BOOKED
            if booking is None:
                raise BookingNotFoundException(
                    f"Booking {booking_id} not found")
            booking.status = BookingStatus.CONFIRMED
            # await db.commit()
            booking_response: BookingResponse = BookingResponse.model_validate(
                booking)
            await redis.set(f"idempotency:{idem_key}", json.dumps(booking_response.model_dump()), ex=600)
        return booking


crud_booking = CRDBooking()
