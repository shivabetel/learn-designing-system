from pydantic import BaseModel
from datetime import datetime
from app.schemas.screen import ScreenResponse

class TheatreBase(BaseModel):
    name: str
    city: str
    address: str
    screens: list[ScreenResponse]

class TheatreCreate(TheatreBase):
    pass

class TheatreUpdate(TheatreBase):
    name: str | None = None
    city: str | None = None
    address: str | None = None



class TheatreResponse(TheatreBase):
    # id: int
    class Config:
        from_attributes = True  # Previously orm_mode
 