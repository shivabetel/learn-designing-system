from pydantic import BaseModel


class BookingSeatBase(BaseModel):    
    booking_id: int
    show_seat_id: int


class BookingSeatCreate(BookingSeatBase):
    pass


class BookingSeatUpdate(BookingSeatBase):
    pass


class BookingSeatResponse(BookingSeatBase):
    id: int

    class Config:
        from_attributes = True
