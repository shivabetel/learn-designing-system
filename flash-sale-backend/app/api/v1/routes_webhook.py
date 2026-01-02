import json
import hmac
import hashlib
import logging
from fastapi import APIRouter, Request, HTTPException, Header
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.db.session import async_session_factory
from app.db.models.order import Order, OrderStatus
from app.db.models.webhook_event import WebhookEvent
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# In production, this would come from environment/secrets
WEBHOOK_SECRET = getattr(settings, 'WEBHOOK_SECRET', 'whsec_test_secret')


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify webhook signature (Stripe-style HMAC-SHA256).
    In production, use the actual gateway's verification method.
    """
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post("/payments")
async def payment_webhook(
    request: Request,
    x_webhook_signature: str = Header(None, alias="X-Webhook-Signature")
):
    """
    Handle payment gateway webhook callbacks.

    Idempotency is guaranteed by:
    1. Storing event_id in DB with unique constraint
    2. Checking if event already processed before taking action
    3. Using IntegrityError to catch concurrent duplicates

    Event types handled:
    - payment.succeeded: Mark order as CONFIRMED
    - payment.failed: Mark order as FAILED, restore inventory
    """

    # 1. Read raw payload
    payload = await request.body()

    # 2. Verify signature (skip in development)
    if settings.ENV != 'development':
        if not x_webhook_signature:
            raise HTTPException(status_code=401, detail="Missing signature")
        if not verify_signature(payload, x_webhook_signature, WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid signature")

    # 3. Parse event
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_id = event.get("id")
    event_type = event.get("type")
    data = event.get("data", {})

    if not event_id or not event_type:
        raise HTTPException(status_code=400, detail="Missing event_id or type")

    logger.info(f"Received webhook: {event_type} (id: {event_id})")

    # 4. Idempotency check - try to insert event record
    async with async_session_factory() as db:
        try:
            db.add(WebhookEvent(
                event_id=event_id,
                event_type=event_type,
                payload=json.dumps(data)
            ))
            await db.commit()
        except IntegrityError:
            # Event already processed - return success (idempotent)
            await db.rollback()
            logger.info(f"Webhook {event_id} already processed, skipping")
            return {"status": "already_processed", "event_id": event_id}

    # 5. Process based on event type
    order_id = data.get("order_id")

    if not order_id:
        logger.warning(f"Webhook {event_id} missing order_id in data")
        return {"status": "ignored", "reason": "missing order_id"}

    if event_type == "payment.succeeded":
        await handle_payment_success(order_id, event_id)

    elif event_type == "payment.failed":
        await handle_payment_failure(order_id, event_id)

    else:
        logger.info(f"Unhandled event type: {event_type}")
        return {"status": "ignored", "event_type": event_type}

    return {"status": "processed", "event_id": event_id}


async def handle_payment_success(order_id: str, event_id: str):
    """
    Handle successful payment - update order to CONFIRMED.

    Idempotent: Only updates if status is PENDING.
    """
    async with async_session_factory() as db:
        # Only update PENDING orders (guard against duplicate updates)
        result = await db.execute(
            update(Order)
            .where(Order.order_id == order_id)
            .where(Order.status == OrderStatus.PENDING)
            .values(status=OrderStatus.CONFIRMED)
        )
        await db.commit()

        if result.rowcount > 0:
            logger.info(f"Order {order_id} confirmed via webhook {event_id}")
        else:
            logger.info(
                f"Order {order_id} not updated (already processed or not found)")


async def handle_payment_failure(order_id: str, event_id: str):
    """
    Handle failed payment - update order to FAILED and restore inventory.

    Idempotent: Only updates if status is PENDING.
    """
    async with async_session_factory() as db:
        # Get order details before updating (need product_id for inventory restore)
        order_result = await db.execute(
            select(Order).where(Order.order_id == order_id)
        )
        order = order_result.scalar_one_or_none()

        if not order:
            logger.warning(
                f"Order {order_id} not found for webhook {event_id}")
            return

        if order.status != OrderStatus.PENDING:
            logger.info(
                f"Order {order_id} already in status {order.status}, skipping")
            return

        # Update status to FAILED
        await db.execute(
            update(Order)
            .where(Order.order_id == order_id)
            .where(Order.status == OrderStatus.PENDING)
            .values(status=OrderStatus.FAILED)
        )
        await db.commit()

        logger.info(f"Order {order_id} marked FAILED via webhook {event_id}")

        # Restore inventory in Redis
        await restore_inventory(order.flash_sale_id, order.product_id)


async def restore_inventory(flash_sale_id: int, product_id: int):
    """
    Restore inventory to Redis after failed/expired order.
    """
    from app.redis import redis_client

    prefix_tag = f"flashsale:{{{flash_sale_id}:{product_id}}}"
    inventory_key = f"{prefix_tag}:stock"

    await redis_client.incr(inventory_key)
    logger.info(f"Restored 1 unit to {inventory_key}")
