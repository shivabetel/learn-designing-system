from pydantic import BaseModel

from app.models.Seat import ShowSeatStatus


class ShowSeatBase(BaseModel):
    show_id: int
    seat_id: int
    status: ShowSeatStatus
    price: float


class ShowSeatCreate(ShowSeatBase):
    pass


class ShowSeatUpdate(ShowSeatBase):
    pass


class ShowSeatResponse(ShowSeatBase):
    id: int

    class Config:
        from_attributes = True
