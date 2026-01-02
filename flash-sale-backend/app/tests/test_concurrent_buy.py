import pytest
from app.services.inventory import inventory_service
from app.schemas.buy import BuyRequest
from app.exception import OutOfStockException, UserAlreadyPurchasedException
import asyncio


@pytest.fixture
async def setup_inventory(redis_client):
    """
    Setup inventory for the test.
    """
    flash_sale_id = 1111
    product_id = 123456
    initial_quantity = 4
    user_ids = [f"user_{i}" for i in range(5)]

    inventory_key = f"flashsale:{{{flash_sale_id}:{product_id}}}:stock"
    await redis_client.set(inventory_key, initial_quantity)
    yield {"flash_sale_id": flash_sale_id, "product_id": product_id, "initial_quantity": initial_quantity, "user_ids": user_ids}

    await redis_client.delete(inventory_key)
    keys = await redis_client.keys(f"flashsale:{{{flash_sale_id}:{product_id}}}:user:*")
    if keys:
        await redis_client.delete(*keys)


@pytest.mark.asyncio
async def test_concurrent_buy(redis_client, setup_inventory):
    """
    Test: Concurrent buy requests. should not overbuy the inventory.
    """
    flash_sale_id = setup_inventory["flash_sale_id"]
    product_id = setup_inventory["product_id"]
    user_ids = setup_inventory["user_ids"]

    async def make_request(user_id, flash_sale_id, product_id):
        try:
            result = await inventory_service.reserve_inventory(BuyRequest(flash_sale_id=flash_sale_id, product_id=product_id, user_id=user_id), redis=redis_client)
            return {"success": True, "result": result}
        except OutOfStockException:
            return {"success": False, "error": "out_of_stock"}
        except UserAlreadyPurchasedException:
            return {"success": False, "error": "user_already_purchased"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    cors = [make_request(user_id, flash_sale_id, product_id)
            for user_id in user_ids]
    results = await asyncio.gather(*cors, return_exceptions=True)

    successful_results = [result for result in results if result["success"]]
    failed_results = [result for result in results if not result["success"]]

    assert len(
        successful_results) == 4, f"Expected 4 successful results, got {len(successful_results)}. Results: {successful_results}"
    assert len(
        failed_results) == 1, f"Expected 1 failed result, got {len(failed_results)}. Results: {failed_results}"
    assert failed_results[0][
        "error"] == "out_of_stock", f"Expected out_of_stock error, got {failed_results[0]['error']}. Results: {failed_results}"


async def test_same_user_concurrent_buy(redis_client, setup_inventory):
    flash_sale_id = setup_inventory["flash_sale_id"]
    product_id = setup_inventory["product_id"]
    user_id = setup_inventory["user_ids"][0]

    async def make_request(user_id, flash_sale_id, product_id):
        try:
            result = await inventory_service.reserve_inventory(BuyRequest(flash_sale_id=flash_sale_id, product_id=product_id, user_id=user_id), redis=redis_client)
            return {"success": True, "result": result}
        except OutOfStockException:
            return {"success": False, "error": "out_of_stock"}
        except UserAlreadyPurchasedException:
            return {"success": False, "error": "user_already_purchased"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    cors = [make_request(user_id=user_id, flash_sale_id=flash_sale_id, product_id=product_id) for i in range(2)]
    results = await asyncio.gather(*cors, return_exceptions=True)
    successful_results = [result for result in results if result["success"]]
    failed_results = [result for result in results if not result["success"]]

    assert len(successful_results) == 1, f"Expected 1 successful result, got {len(successful_results)}. Results: {successful_results}"
    assert len(failed_results) == 1, f"Expected 1 failed result, got {len(failed_results)}. Results: {failed_results}"
    assert failed_results[0]["error"] == "user_already_purchased", f"Expected user_already_purchased error, got {failed_results[0]['error']}. Results: {failed_results}"
