from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class OptionBase(BaseModel):
    text: str


class OptionCreate(OptionBase):
    pass


class OptionResponse(OptionBase):
    id: int

    class Config:
        from_attributes = True


class OptionWithVotes(OptionResponse):
    vote_count: int
    percentage: float


class PollBase(BaseModel):
    question: str


class PollCreate(PollBase):
    options: List[str]  # List of option texts


class PollResponse(PollBase):
    id: int
    status: str
    options: List[OptionResponse]
    created_at: datetime

    class Config:
        from_attributes = True


class PollListResponse(BaseModel):
    id: int
    question: str
    status: str
    option_count: int
    total_votes: int
    created_at: datetime


class PollResultsResponse(BaseModel):
    id: int
    question: str
    total_votes: int
    options: List[OptionWithVotes]

