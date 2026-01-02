from pydantic import BaseModel

from app.models.booking import BookingStatus


class BookingBase(BaseModel):    
    status: BookingStatus
    show_id: int
    total_amount: float


class BookingCreate(BookingBase):
    pass


class BookingUpdate(BookingBase):
    pass


class BookingResponse(BookingBase):
    id: int

    class Config:
        from_attributes = True
