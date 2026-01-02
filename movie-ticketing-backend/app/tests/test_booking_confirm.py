from app.crud.booking import crud_booking
from app.models.booking import BookingStatus


async def test_booking_confirm(seeded_test_data, db_session_factory, redis_client):
    session = db_session_factory()
    show_id = seeded_test_data["show_id"]
    show_seat_ids = seeded_test_data["show_seat_ids"]
    booking_id = await crud_booking.lock_seats(
        session, redis_client, show_id, show_seat_ids)
    booking = await crud_booking.confirm_booking(booking_id=booking_id, db=session, idem_key="test", redis=redis_client)
    assert booking.status == BookingStatus.CONFIRMED
