import asyncio
from random import random


class PaymentService:
    async def process_payment(self, order_id: str, idempotency_key: str):
        # while calling payment gateway, we will pass idempotency_key. this will help us to avoid duplicate payments.
        # Gateway	Idempotency Mechanism
        # Stripe	Idempotency-Key header (you provide)
        # PayPal	PayPal-Request-Id header
        # Razorpay	X-Razorpay-Idempotency-Key header
        # Square	Idempotency-Key header
        # Adyen	rreference field (merchant order ID)
        await asyncio.sleep(0.2)
        return random() > 0.1


payment_service = PaymentService()
