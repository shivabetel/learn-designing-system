from pydantic import BaseModel


class VoteRequest(BaseModel):
    poll_id: int
    option_id: int
    user_id: str

class VoteResponse(BaseModel):
    message: str
    success: bool