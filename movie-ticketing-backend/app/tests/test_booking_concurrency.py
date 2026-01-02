from sqlalchemy import exc
from sqlalchemy.ext.asyncio import async_sessionmaker
import pytest
from redis.asyncio import Redis
from app.crud.booking import crud_booking
from app.exceptions.seat_already_locked import SeatAlreadyLockedException
from app.core.config import settings
import asyncio


@pytest.fixture
def test_show_id(seeded_test_data):
    """Get the show ID from seeded test data."""
    return seeded_test_data["show_id"]


@pytest.fixture
def test_show_seat_ids(seeded_test_data):
    """Get the show seat IDs from seeded test data."""
    return seeded_test_data["show_seat_ids"]


@pytest.mark.asyncio
async def test_concurrent_same_seats_booking(db_engine, test_show_id, test_show_seat_ids, redis_client):
    """Test concurrent booking attempts on same seats - only one should succeed."""
    num_of_concurrent_requests = 10

    async_session_factory = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False
    )

    async def make_request(booking_num):
        """Make a booking request with its own session and Redis client."""
        # Create a fresh Redis client for each request
        # redis = Redis.from_url(
        #     settings.REDIS_URL,
        #     decode_responses=False,
        #     socket_connect_timeout=2
        # )
        session = async_session_factory()
        try:
            booking_id = await crud_booking.lock_seats(
                session,
                redis_client,
                test_show_id,
                test_show_seat_ids
            )
            await session.commit()
            return {"success": True, "booking_id": booking_id, "request": booking_num}
        except SeatAlreadyLockedException:
            await session.rollback()
            return {"success": False, "error": "locked", "request": booking_num}
        except Exception as e:
            await session.rollback()
            return {"success": False, "error": str(e), "request": booking_num}
        finally:
            await session.close()
            # await redis.aclose()

    # Execute all requests concurrently
    coros = [make_request(i) for i in range(num_of_concurrent_requests)]
    results = await asyncio.gather(*coros, return_exceptions=True)

    # Process results and handle exceptions
    # processed_results = []
    # for i, result in enumerate(results):
    #     if isinstance(result, Exception):
    #         processed_results.append({"success": False, "error": str(result), "request": i})
    #     else:
    #         processed_results.append(result)

    # print("\n" + "="*60)
    # print("CONCURRENCY TEST RESULTS:")
    # for r in processed_results:
    #     status = "✅ SUCCESS" if r.get("success") else "❌ FAILED"
    #     print(f"  Request {r.get('request')}: {status} - {r.get('error', r.get('booking_id', ''))}")
    # print("="*60)

    successful_bookings = [r for r in results if r['success']]
    failed_bookings = [r for r in results if not r['success']]

    # Assertions
    assert len(
        successful_bookings) == 1, f"Expected 1 success, got {len(successful_bookings)}. Results: {successful_bookings}"
    assert len(failed_bookings) == num_of_concurrent_requests - \
        1, f"Expected {num_of_concurrent_requests - 1} failures"
    assert all(
        r['error'] == "locked" for r in failed_bookings), f"Not all failures were due to locking. Results: {failed_bookings}"

    print(
        f"\n✅ Test passed! Only 1 booking succeeded out of {num_of_concurrent_requests} concurrent requests.")


@pytest.mark.asyncio
async def test_concurrent_different_seats(seeded_test_data, db_session_factory, redis_client):
    """
     Test: Multiple users try to book overlapping seats
    Expected: At most one booking succeeds for each seat
    """
    show_id = seeded_test_data["show_id"]
    seat_sets = [
        [1, 2],
        [3, 4],
        [5, 6],
        # [7, 8],
    ]

    async def make_request(show_id, show_seat_ids):
        session = db_session_factory()
        try:
            booking_id = await crud_booking.lock_seats(
                session,
                redis_client,
                show_id,
                show_seat_ids)
            return {"success": True, "booking_id": booking_id}  # <-- ADD THIS
        except SeatAlreadyLockedException:
            return {"success": False, "error": "locked"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    cors = [make_request(show_id, show_seats) for show_seats in seat_sets]
    results = await asyncio.gather(*cors, return_exceptions=True)

    successful_bookings = [r for r in results if r['success']]
    failed_bookings = [r for r in results if not r['success']]

    assert len(successful_bookings) == len(
        seat_sets), f"expected {len(seat_sets)} successes, got {len(successful_bookings)}. Results: {successful_bookings}"
    assert len(
        failed_bookings) == 0, f"expected 0 failures, got {len(failed_bookings)}. Results: {failed_bookings}"


@pytest.mark.asyncio
async def test_booking_concurrency_overlapping_seats(seeded_test_data, db_session_factory, redis_client):
    show_id = seeded_test_data["show_id"]
    seats_sets = [
        [1, 2],
        [3, 4],
        [2, 3],
        [4, 5]
    ]

    async def make_request(show_id, show_seat_ids):
        try:
            session = db_session_factory()
            booking_id = await crud_booking.lock_seats(
                db=session,
                redis=redis_client,
                show_id=show_id,
                show_seat_ids=show_seat_ids
            )
            return {"success": True, "booking_id": booking_id}
        except SeatAlreadyLockedException:
            return {"success": False, "error": "locked"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            session.close()
    cors = [make_request(show_id=show_id, show_seat_ids=show_seatIds)
            for show_seatIds in seats_sets]
    results = await asyncio.gather(*cors, return_exceptions=True)

    successful_bookings = [result for result in results if result['success']]
    failed_bookings = [result for result in results if not result['success']]

    assert len(
        successful_bookings) == 2, f"expected 2 successess, got {len(successful_bookings)}. Results: {successful_bookings}"
    assert len(
        failed_bookings) == 2, f"expected 2 failures, got {len(failed_bookings)}. Results: {failed_bookings}"
    # assert all(result['error'] == "locked" for result in failed_bookings), f"Not all failures were due to locking. Results: {failed_bookings}"
