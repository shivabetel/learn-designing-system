from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from app.services.inventory import inventory_service
from app.exception import OutOfStockException, UserAlreadyPurchasedException
from app.schemas.buy import BuyRequest
from app.redis import get_redis
router = APIRouter(
    prefix="/inventory"
)


@router.post("/flash-sale/{flash_sale_id}/product/{product_id}/{user_id}/buy")
async def buy(flash_sale_id: int, product_id: int, user_id: str, redis: Redis = Depends(get_redis)):
    try:
        data = BuyRequest(flash_sale_id=flash_sale_id, product_id=product_id, user_id=user_id)
        return await inventory_service.reserve_inventory(data, redis)
    except OutOfStockException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UserAlreadyPurchasedException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
