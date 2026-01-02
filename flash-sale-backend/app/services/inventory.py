from app.schemas.buy import BuyRequest
from redis.asyncio import Redis
from app.exception import OutOfStockException, UserAlreadyPurchasedException
from app.db.models.order import Order, OrderStatus
from uuid import uuid4
from app.services.order_queue import order_queue
from app.schemas.restore_inventory_request import RestoreInventoryRequest

# Redis Hash Tags: {tag} ensures all keys with same tag go to same shard in Redis Cluster
# This is required for Lua scripts to work in cluster mode (avoids CROSSSLOT errors)
# Key pattern: flashsale:{sale_id}:product:{product_id}:stock
# Note: Redis uses FIRST {..} for sharding, so all products in same sale go to same shard
LUA_SCRIPT_INVENTORY_CHECK_AND_DECREMENT = """
-- KEYS[1] = flash_sale_id
-- KEYS[2] = product_id
-- KEYS[3] = user_id
-- ARGV[1] = ttl (seconds)

-- Hash tag ensures all keys go to same shard in Redis Cluster
-- Pattern: flashsale:{sale_id:product_id}:stock
local prefix_tag = "flashsale:{" .. KEYS[1] .. ":" .. KEYS[2] .. "}"
local inventory_key = prefix_tag .. ":stock"
local user_lock_key = prefix_tag .. ":user:" .. KEYS[3]

-- 1. Prevent double buying
local exists = redis.call('EXISTS', user_lock_key)
if exists == 1 then 
   return -2  -- User already purchased
end

-- 2. Read current stock
local stock = redis.call('GET', inventory_key)
if not stock or tonumber(stock) <= 0 then
  return -1  -- Out of stock
end

-- 3. Decrement stock
redis.call('DECR', inventory_key)

-- 4. Lock user to prevent duplicate purchases
redis.call('SET', user_lock_key, "1", "EX", ARGV[1])

return 1  -- Success
"""


class InventoryService:
    async def reserve_inventory(self, data: BuyRequest, redis: Redis):
        result = await redis.eval(LUA_SCRIPT_INVENTORY_CHECK_AND_DECREMENT, 3, data.flash_sale_id, data.product_id, data.user_id, 600)
        if result == 1:
            order_event = {
                "order_id": uuid4(),
                "flash_sale_id": data.flash_sale_id,
                "product_id": data.product_id,
                "status": OrderStatus.PENDING,
            }
            await order_queue.put(order_event)
            return {
                "order_id": order_event["order_id"],
                "message": "Order reserved successfully",
            }
        elif result == -1:
            raise OutOfStockException()
        elif result == -2:
            raise UserAlreadyPurchasedException()
        else:
            raise Exception("Unknown error")

    async def restore_inventory(self, data: RestoreInventoryRequest, redis: Redis):
        product_id = data.product_id
        flash_sale_id = data.flash_sale_id
        quantity = data.quantity
        stock_key = f"flashsale:{{{flash_sale_id}:{product_id}}}:stock"
        pipe = redis.pipeline()
        pipe.incrby(stock_key, quantity)
        pipe.delete(f"flashsale:{{{flash_sale_id}:{product_id}}}:user:*")
        await pipe.execute()


inventory_service = InventoryService()
