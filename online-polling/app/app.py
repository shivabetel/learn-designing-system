from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.models.poll import Poll
from app.models.option import Option
from app.models.vote_log import VoteLog
from app.db.core import init_db
from app.core.config import settings
from app.scripts import seed_data
import app.api.routes_vote as routes_vote
import app.api.routes_poll as routes_poll
import asyncio
from app.workers.redis_update_worker import redis_update_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if settings.ENV == 'development':
        await seed_data.seed_data()
    asyncio.create_task(redis_update_worker.run())    
    yield
    # await session.close()


def create_app():
    app = FastAPI(
        name="Online Polling API",
        version="0.1.0",
        description="API for online polling system",
        lifespan=lifespan
    )

    # Add CORS middleware for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(
        routes_vote.router,
        prefix="/api/v1"
    )
    
    app.include_router(
        routes_poll.router,
        prefix="/api/v1"
    )

    @app.get("/")
    async def hello_world():
        return {"message": "Hello World"}
    return app


app = create_app()
