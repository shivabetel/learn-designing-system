from sqlalchemy.sql import text
from app.db.core import async_session_factory
from app.redis import redis_client

# Lua script for atomic vote processing
PROCESS_VOTE_SCRIPT = """
local already_voted = redis.call('SISMEMBER', KEYS[1], ARGV[1])

if already_voted == 0 then
    redis.call('SADD', KEYS[1], ARGV[1])
    redis.call('INCR', KEYS[2])
end

redis.call('SET', KEYS[3], ARGV[2])

return already_voted == 0 and 1 or 0
"""


class Projection_worker():
    CURSOR_KEY = "worker:vote_log:last_id"

    async def run(self):
        while True:
            async with async_session_factory() as session:
                last_id = int(await redis_client.get(self.CURSOR_KEY) or 0)
                result = await session.execute(text("""
                 select vote_id, poll_id, option_id, user_id from vote_log
                 WHERE created_at <= NOW() - INTERVAL '1 minute'
                 AND vote_id > :last_id
                 """), {
                    "last_id": last_id
                })
                votes = result.fetchall()
                for vote in votes:
                    vote_key = f"poll:{{{vote.poll_id}}}:voters"
                    count_key = f"poll:{{{vote.poll_id}}}:count"
                    # cursor_key = f"poll:{{{vote.poll_id}}}:cursor"
                    # await redis_client.set(f"poll:{{{vote.poll_id}}}", json.dumps(poll))
                    await redis_client.eval(PROCESS_VOTE_SCRIPT, 3, vote_key, count_key, self.CURSOR_KEY, vote.user_id, vote.option_id)


redis_update_worker = Projection_worker()
