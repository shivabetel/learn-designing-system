from pydantic import BaseModel


class ScreenBase(BaseModel):
    name: str
    total_seats: int


class ScreenCreate(ScreenBase):
    pass


class ScreenUpdate(ScreenBase):
    name: str | None = None
    total_seats: int | None = None


class ScreenResponse(ScreenBase):
    id: int
    theatre_id: int
    class Config:
        from_attributes = True  # Previously orm_mode
