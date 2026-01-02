# from os import name
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1 import routes_booking, routes_health, routes_movie, routes_redis, routes_screen, routes_show, routes_theatre
from app.core.config import settings
from app.db import session
from app.models.Movie import Movie
from app.models.Show import Show
from app.models.Theatre import Theatre, Screen
from app.models.Seat import Seat, ShowSeat
from app.models.booking import Booking
from app.models.booking_seat import BookingSeat
from app.scripts import seed_data
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    if (settings.ENV == 'development'):
        await session.init_db()
        # await seed_data.main()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        name="Movie Ticketing API",
        version="0.1.0",
        description="API for movie ticketing system",
        lifespan=lifespan

    )

    # add middleware to check if the request is coming from a trusted source
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(
        routes_health.router,
        prefix="/api/v1"
    )
    app.include_router(
        routes_theatre.router,
        prefix="/api/v1"
    )
    app.include_router(
        routes_screen.router,
        prefix="/api/v1"
    )

    app.include_router(
        routes_movie.router,
        prefix="/api/v1"
    )

    app.include_router(
        routes_show.router,
        prefix="/api/v1"
    )

    app.include_router(
        routes_redis.router,
        prefix="/api/v1"
    )

    app.include_router(
        routes_booking.router,
        prefix="/api/v1"
    )

    @app.get("/")
    async def root():
        return {"message": "Movie ticketing backend is running"}

    @app.get("/hello_world")
    async def hello_world():
        return {"message": "Hello world"}
    return app


app = create_app()
