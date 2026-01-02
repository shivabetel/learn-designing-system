from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import text, update
from app.services.order_queue import order_queue
from app.db.session import async_session_factory
from app.db.models.order import Order, OrderStatus
from app.services.payment import payment_service
from app.services.inventory import inventory_service
from app.schemas.restore_inventory_request import RestoreInventoryRequest


insert_order_sql = """
INSERT INTO orders (order_id, flash_sale_id, product_id, status, created_at, updated_at) VALUES (:order_id, :flash_sale_id, :product_id, :status, NOW(), NOW())
ON CONFLICT (order_id) DO NOTHING
"""

update_order_to_payment_in_progress_sql = """
UPDATE orders SET status = 'PAYMENT_IN_PROGRESS', updated_at = NOW() WHERE order_id = :order_id and status = 'PENDING'
"""


update_order_to_payment_success_sql = """
UPDATE orders SET status = 'CONFIRMED', updated_at = NOW() WHERE order_id = :order_id and status = 'PAYMENT_IN_PROGRESS'
"""

update_order_to_payment_failed_sql = """
UPDATE orders SET status = 'FAILED', updated_at = NOW() WHERE order_id = :order_id and status = 'PAYMENT_IN_PROGRESS'
"""

# Notes:
# What If Worker Crashes After Payment Success?

# This will happen.

# Protection layers:

# Gateway idempotency prevents re-charge

# Webhook callback updates order status

# Order status guard prevents re-payment


async def order_worker():
    while True:
        event = await order_queue.get()
        try:
            async with async_session_factory() as db:
                # if event is replayed, nothing happens in this insert operation.
                await db.execute(text(insert_order_sql, {
                    "order_id": event['order_id'],
                    "flash_sale_id": event['flash_sale_id'],
                    "product_id": event['product_id'],
                    "status": event['status'],
                }))
                await db.commit()  # if worker crashes here, order will be in PENDING state
            async with async_session_factory() as db:
                # if event is replayed, nothing happens in this update operation if order is not in PENDING state.
                result = await db.execute(text(update_order_to_payment_in_progress_sql, {
                    "order_id": event['order_id'],
                }))
                row = result.fetchone()
                await db.commit()
                if row is None:
                    # Someone else already processed this order
                    continue
                # if worker crashes after db.commit(), order will be in PAYMENT_IN_PROGRESS state.
                # this state will hanging as request will never reach payment gateway. and there is no way payment gateway will update the order status via webhook.
                # we need reaper job to handle this state. clean up these orders and restore inventory.
            payment_result = await payment_service.process_payment(event['order_id'], idempotency_key=event['order_id'])
            # if worker crashes after payment_result, order will be in PAYMENT_IN_PROGRESS state.
            # since request reached payment gateway, payment gateway will update the order status via webhook.
            async with async_session_factory() as db:
                if (not payment_result):
                    result = await db.execute(text(update_order_to_payment_failed_sql, {
                        "order_id": event['order_id'],
                    }))
                    row = result.fetchone()
                    if row is not None:
                        # Someone else already processed this order
                        await inventory_service.restore_inventory(RestoreInventoryRequest(product_id=event['product_id'], flash_sale_id=event['flash_sale_id'], quantity=1))
                    await db.commit()
                else:
                    await db.execute(text(update_order_to_payment_success_sql, {
                        "order_id": event['order_id'],
                    }))
                    await db.commit()
        except Exception as ex:
            # should i do stock rollback here?
            # or should i do retries?
            pass
        finally:
            order_queue.task_done()

# async def order_worker():
#     while True:
#         event = await order_queue.get()
#         try:
#             async with async_session_factory() as db:
#                 try:
#                     # idempotency check
#                     # existing_order_result = await db.execute(select(Order).where(Order.order_id == event['order_id']))
#                     # existing_order = existing_order_result.scalar_one_or_none()
#                     # if existing_order:
#                     #     continue
#                     db.add(Order(
#                         order_id=str(event['order_id']),
#                         flash_sale_id=int(event['flash_sale_id']),
#                         product_id=int(event['product_id']),
#                         status=OrderStatus(event['status']),
#                     ))
#                     await db.commit()
#                 except IntegrityError:
#                     # this will take care of idempotency check
#                     await db.rollback()
#                     continue

#             payment_result = await payment_service.process_payment(event['order_id'])
#             async with async_session_factory() as db:
#                 status = OrderStatus.CONFIRMED
#                 if (not payment_result):
#                     status = OrderStatus.FAILED

#                 await db.execute(update(Order).where(Order.order_id == str(
#                     event['order_id'])).values(status=status))
#                 await db.commit()

#         except Exception as ex:
#             # should i do stock rollback here?
#             # or should i do retries?
#             pass
#         finally:
#             order_queue.task_done()
