from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.db.core import init_db
import app.api.routes_health as routes_health
import app.api.routes_wallet as routes_wallet
from app.core.exceptions import WalletError


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting up...")
    await init_db()
    yield  # App runs here
    # SHUTDOWN
    print("🛑 Shutting down...")


def create_app():
    app = FastAPI(
        title=settings.APP_NAME,
        lifespan=lifespan
    )

    app.include_router(
        routes_health.router,
        prefix="/api/v1"
    )

    app.include_router(
        routes_wallet.router,
        prefix="/api/v1"
    )

    @app.exception_handler(WalletError)
    async def wallet_error_handler(request, ex):
        print("inside global error handler")
        return JSONResponse(status_code=ex.status_code, content={"error": ex.message})

    @app.get("/")
    def hello_world():
        return "hello world"
    return app


app = create_app()
