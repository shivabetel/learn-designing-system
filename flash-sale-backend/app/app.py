import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.db import session
from app.db.models.product import Product
from app.db.models.flash_sale import FlashSale
import app.db.models.flash_sale_product
import app.db.models.order
import app.db.models.webhook_event
from app.api.v1 import routes_inventory, routes_webhook
from app.workers.order_worker import order_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENV == 'development':
        await session.init_db()
        await session.preload_inventory()

    asyncio.create_task(order_worker())
    yield


def create_app():
    app = FastAPI(
        name="Flash Sale API",
        version="1.0.0",
        description="API for flash sale system",
        lifespan=lifespan
    )

    app.include_router(
        routes_inventory.router,
        prefix="/api/v1"
    )

    app.include_router(
        routes_webhook.router,
        prefix="/api/v1/webhooks",
        tags=["webhooks"]
    )

    @app.get("/")
    def root():
        return {"message": "Flash sale api backend"}
    return app


app = create_app()
