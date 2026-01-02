from datetime import datetime
from pydantic import BaseModel


class ShowBase(BaseModel):
    start_time: datetime
    end_time: datetime
    base_price: float


class ShowCreate(ShowBase):
    pass


class ShowUpdate(ShowBase):
    pass


class ShowResponse(ShowBase):
    id: int
    movie_id: int
    screen_id: int

    class Config:
        from_attributes = True  # orm_mode
