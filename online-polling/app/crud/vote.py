from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from app.schemas.vote import VoteRequest
from app.models.vote_log import VoteLog
from sqlalchemy.exc import IntegrityError
from app.exceptions.vote_already_exists_exception import VoteAlreadyExistsException


INSERT_VOTE_LOG_SQL = """
INSERT INTO vote_log (poll_id, option_id, user_id, created_at, updated_at) VALUES (:poll_id, :option_id, :user_id, NOW(), NOW())
ON CONFLICT (poll_id, user_id) DO NOTHING
"""


class CRUDVote:
    async def create_vote(self, db: AsyncSession, vote_request: VoteRequest):
        try:
            # vote = VoteLog(
            #     poll_id=vote_request.poll_id,
            #     option_id=vote_request.option_id,
            #     user_id=vote_request.user_id,
            # )
            # db.add(vote)
            # await db.commit()
            # await db.refresh(vote)
            # return vote
            result = await db.execute(text(INSERT_VOTE_LOG_SQL),
                                      {
                                          "poll_id": vote_request.poll_id,
                                          "option_id": vote_request.option_id,
                                          "user_id": vote_request.user_id,

            })
            await db.commit()
            if result.rowcount == 0:
                raise VoteAlreadyExistsException(
                    f"Vote already exists for poll {vote_request.poll_id} and user {vote_request.user_id}")
            return {
                "poll_id": vote_request.poll_id,
                "option_id": vote_request.option_id,
                "user_id": vote_request.user_id,
                "status": "voted"
            }

        # except IntegrityError as e:
        #     await db.rollback()
        #     raise VoteAlreadyExistsException(
        #         f"Vote already exists for poll {vote_request.poll_id} and user {vote_request.user_id}")
        except Exception as e:
            await db.rollback()
            raise e


crud_vote = CRUDVote()
