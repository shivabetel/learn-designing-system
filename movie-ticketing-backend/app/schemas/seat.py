from pydantic import BaseModel

from app.models.Seat import SeatType


class SeatBase(BaseModel):
    seat_number: int
    row_label: str
    seat_type: SeatType    


class SeatCreate(SeatBase):
    pass


class SeatUpdate(SeatBase):
    pass


class SeatResponse(SeatBase):
    id: int

    class Config:
        from_attributes = True
