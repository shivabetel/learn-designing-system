from typing import Optional
from pydantic import BaseModel

from app.models.Movie import Certificate


class MovieBase(BaseModel):
    title: str
    description: str
    duration_mins: int
    language: str
    certificate: Optional[Certificate] = None


class MovieCreate(MovieBase):
    pass


class MovieUpdate(MovieBase):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_mins: Optional[int] = None
    language: Optional[str] = None
    certificate: Optional[Certificate] = None


class MovieResponse(MovieBase):
    id: int

    class Config:
        from_attributes = True  # orm_mode
