# Flash Sale Backend

A high-performance backend system designed to handle extreme traffic during flash sale events.

---

## Scale Requirements

| Metric | Value |
|--------|-------|
| Users online | 50 million |
| Active in first 10 mins | 10 million |
| Buy attempts in first 30 sec | 2 million |
| **Target RPS** | **100k** (accounting for retries & bots) |

> **Calculation:** 2,000,000 ÷ 30 = ~66,667 requests/second base load

---

## Functional Requirements

1. Create flash sale event
2. List flash sale products
3. Show remaining inventory
4. Allow user to attempt purchase
5. **Guarantee no overselling**
6. Confirm or reject order immediately
7. Handle payment asynchronously

---

## Non-Functional Requirements

### 1. Latency
- Buy API **p99 < 100ms**

### 2. Availability
Buy API must stay up even if:
- Order DB is slow
- Payment service is down

### 3. Consistency
> **Choosing consistency over availability**
- Inventory correctness > availability
- Better to reject users than oversell

---

## Why Redis for Inventory?

Redis supports atomic in-memory operations (like `DECR`) that can handle **tens of thousands of concurrent writes per second** on the same key.

Traditional databases rely on disk I/O and locking mechanisms, which **collapse under high write contention**, making them unsuitable for flash sale inventory control.

---

## Design Decisions & Trade-offs

### ❌ Why We Avoid Foreign Keys in Flash-Sale Order Tables

Foreign keys introduce **synchronous cross-table checks and locks**, which collapse under extreme write concurrency.

#### What a Foreign Key Actually Does (Under the Hood)

When you add a foreign key like `orders.product_id → products.id`:

Every `INSERT` into orders requires the database to:
1. Check that the referenced row exists in `products`
2. Acquire shared locks on parent rows
3. Maintain referential integrity synchronously

> ⚠️ **This is not free** — it happens inside the transaction.

#### During a Flash Sale

- 50k–100k order inserts/sec
- All inserts reference the **same** `flash_sale_id` and `product_id`

**Result:**
| Problem | Impact |
|---------|--------|
| Hot parent rows | Lock contention |
| Transaction serialization | Throughput collapse |

> 💥 **Your DB becomes the bottleneck** — not CPU, not network.

---

### ❌ Why We Don't Use `orders` + `order_details` Pattern

In a flash sale:
- User clicks **Buy Now**
- Exactly **1 product**
- Quantity = **1**
- No cart
- No modification
- No aggregation logic

> 👉 Each request is an **independent race for inventory**.

#### Why `order_items` Is Dangerous at Scale

**1. Extra Writes (Fatal at 100k RPS)**

Each purchase would require:
- Insert into `orders`
- Insert into `order_items`

That's **2 DB writes per request**. At 100k RPS = **200k inserts/sec**

**2. Foreign Key Locking (Even Worse)**

If `order_items.order_id → orders.id`:
- Parent row locks
- Child row locks
- Transaction serialization

---

### ✅ Why a Single `orders` Table Works Better

| Benefit | Description |
|---------|-------------|
| ✔ Single insert | One write per order |
| ✔ No joins | Faster queries |
| ✔ No aggregation | Simpler logic |
| ✔ Append-only | Linear scalability |

> 📌 This is **event sourcing–friendly**.

---

## Architecture Summary

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   API GW    │────▶│  Buy API    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                         ┌─────────────────────┼─────────────────────┐
                         ▼                     ▼                     ▼
                  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
                  │    Redis    │       │  Orders DB  │       │  Payment    │
                  │ (Inventory) │       │ (Append-only)│      │  (Async)    │
                  └─────────────┘       └─────────────┘       └─────────────┘
```

---

## ❌ Why Database-Based Inventory Fails

When you store inventory in a traditional RDBMS (PostgreSQL, MySQL) and try to decrement it during a flash sale, the system collapses. Here's why:

### Approach 1: Pessimistic Locking (Row Locks)

```sql
BEGIN;
SELECT quantity FROM inventory WHERE product_id = ? FOR UPDATE;
-- Check if quantity > 0
UPDATE inventory SET quantity = quantity - 1 WHERE product_id = ?;
COMMIT;
```

#### What Goes Wrong

| Problem | Explanation |
|---------|-------------|
| **Row Lock Contention** | `FOR UPDATE` acquires an exclusive lock. With 100k concurrent requests hitting the **same row**, 99,999 must wait in line. |
| **Lock Wait Timeouts** | Requests queue up; most exceed timeout thresholds and fail. |
| **Deadlocks** | Multiple transactions competing for the same resources cause deadlock detection overhead and transaction rollbacks. |
| **Connection Pool Exhaustion** | Blocked transactions hold DB connections; pool fills up → new requests rejected. |
| **Throughput Collapse** | Effective throughput drops to **< 1,000 TPS** despite hardware capacity. |

> ⏱️ **Reality:** A single hot row with `FOR UPDATE` can only sustain ~500-2,000 writes/sec regardless of how powerful your DB is.

---

### Approach 2: Optimistic Locking (Version Check)

```sql
UPDATE inventory 
SET quantity = quantity - 1, version = version + 1 
WHERE product_id = ? AND quantity > 0 AND version = ?;
```

#### What Goes Wrong

| Problem | Explanation |
|---------|-------------|
| **Retry Storms** | When update fails (version mismatch), client retries. At 100k RPS, failed requests retry → **200k+ actual requests**. |
| **Cascading Failures** | Retries compound exponentially; system load spirals out of control. |
| **Unfair Distribution** | Fast clients win repeatedly; slow clients starve (no fairness guarantee). |
| **DB Saturation** | Even though writes are non-blocking, the sheer volume of read-modify-write cycles saturates disk I/O and CPU. |

> 🔁 **Reality:** Optimistic locking trades lock contention for retry storms — both fail at flash-sale scale.

---

### The Fundamental Problem

```
┌─────────────────────────────────────────────────────────────┐
│                    SINGLE HOT ROW                          │
│                   (inventory: 1000)                        │
└─────────────────────────────────────────────────────────────┘
                            ▲
          ┌─────────────────┼─────────────────┐
          │                 │                 │
     100k requests     100k requests     100k requests
          │                 │                 │
          ▼                 ▼                 ▼
    ┌──────────┐      ┌──────────┐      ┌──────────┐
    │ Thread 1 │      │ Thread 2 │      │ Thread N │
    │  WAITING │      │  WAITING │      │  WAITING │
    └──────────┘      └──────────┘      └──────────┘
```

| Database Constraint | Impact |
|---------------------|--------|
| **Disk I/O** | Every write must be persisted (fsync) for durability |
| **MVCC Overhead** | Multi-version concurrency creates version chain bloat |
| **WAL Bottleneck** | Write-ahead log becomes single point of serialization |
| **Single Row = Single Lock** | No parallelism possible on same row |

> 📌 **Databases are designed for distributed workloads across many rows — NOT for hot-row write contention.**

---

### ✅ Why Redis Works Instead

| Redis Advantage | Explanation |
|-----------------|-------------|
| **In-Memory** | No disk I/O latency; operations complete in microseconds |
| **Single-Threaded** | No lock contention; commands execute sequentially at ~100k ops/sec |
| **Atomic `DECR`** | `DECR inventory:product_123` is atomic — no read-modify-write cycle |
| **Lua Scripts** | Complex logic (check + decrement) runs atomically server-side |

```lua
-- Atomic inventory check and decrement in Redis
local stock = redis.call('GET', KEYS[1])
if tonumber(stock) > 0 then
    redis.call('DECR', KEYS[1])
    return 1  -- Success
end
return 0  -- Sold out
```

> 🚀 **Redis can handle 100k+ atomic decrements/sec on a single key** — exactly what flash sales need.



---

## 🚧 Problems We Must Solve

| Problem | Description |
|---------|-------------|
| **Worker crashes after inserting PENDING** | Order stuck in limbo; inventory reserved but never fulfilled |
| **Payment times out and retries** | Duplicate charges or inconsistent order state |
| **Same order event is processed twice** | Idempotency required to prevent duplicate fulfillment |
| **Inventory reserved but order never confirmed** | Leaked inventory; stock becomes unavailable indefinitely |
| **Queue grows faster than workers** | Backpressure and latency spikes; potential OOM or message loss |

> ⚠️ These are critical edge cases that must be handled for production reliability.

---

## ✅ Solutions

### 1. Worker Crashes After Inserting PENDING

**Problem:** Worker dies after creating a PENDING order but before completing payment/fulfillment.

**Solution: Transactional Outbox Pattern + Reaper Job**

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Buy API    │────▶│  Orders DB  │────▶│  Outbox     │
│             │     │  (PENDING)  │     │  Table      │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                         ┌─────────────────────┘
                         ▼
                  ┌─────────────┐
                  │  Relay Job  │──── Publishes to Queue
                  └─────────────┘
```

| Component | Responsibility |
|-----------|----------------|
| **Outbox Table** | Store events atomically with order insert (same transaction) |
| **Relay Job** | Poll outbox, publish to message queue, mark as sent |
| **Reaper Job** | Find PENDING orders older than X minutes → retry or cancel |

```sql
-- Atomic insert: order + outbox event in same transaction
BEGIN;
INSERT INTO orders (id, status) VALUES (uuid, 'PENDING');
INSERT INTO outbox (order_id, event_type, payload) VALUES (uuid, 'ORDER_CREATED', '{}');
COMMIT;
```

---

### 2. Payment Times Out and Retries

**Problem:** Payment gateway times out; client retries → potential double charge.

**Solution: Idempotency Keys**

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  Payment    │────▶│  Gateway    │
│ (retry)     │     │  Service    │     │             │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │ Idempotency │
                    │    Store    │
                    └─────────────┘
```

| Strategy | Implementation |
|----------|----------------|
| **Idempotency Key** | Client sends unique key per purchase attempt |
| **Deduplication** | Store `idempotency_key → result` in Redis/DB |
| **Return Cached** | If key exists, return stored result (no retry to gateway) |

```python
async def process_payment(order_id: str, idempotency_key: str):
    # Check if already processed
    cached = await redis.get(f"payment:{idempotency_key}")
    if cached:
        return json.loads(cached)  # Return cached result
    
    # Process payment
    result = await payment_gateway.charge(order_id)
    
    # Cache result with TTL
    await redis.setex(f"payment:{idempotency_key}", 86400, json.dumps(result))
    return result
```

---

### 3. Same Order Event Processed Twice

**Problem:** Message queue delivers same event twice (at-least-once delivery).

**Solution: Idempotent Consumers**

| Strategy | Implementation |
|----------|----------------|
| **Processed Event Log** | Track `event_id` in DB before processing |
| **Unique Constraints** | DB rejects duplicate inserts |
| **Check-Then-Act** | Verify order state before state transition |

```python
async def handle_order_event(event: OrderEvent):
    # Check if already processed
    exists = await db.execute(
        "SELECT 1 FROM processed_events WHERE event_id = ?", 
        event.id
    )
    if exists:
        return  # Already processed, skip
    
    # Process in transaction
    async with db.transaction():
        await process_order(event)
        await db.execute(
            "INSERT INTO processed_events (event_id, processed_at) VALUES (?, NOW())",
            event.id
        )
```

---

### 4. Inventory Reserved but Order Never Confirmed

**Problem:** Redis inventory decremented, but order fails downstream → stock leaked.

**Solution: Periodic Reaper Job**

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Orders DB  │────▶│  Reaper Job │────▶│   Redis     │
│  (PENDING)  │     │  (periodic) │     │   (INCR)    │
└─────────────┘     └─────────────┘     └─────────────┘
```

**How It Works:**

1. Job runs every **1-5 minutes** (configurable)
2. Finds orders with `status = 'PENDING'` older than threshold (e.g., 10 minutes)
3. For each stuck order:
   - Restore inventory in Redis (`INCR`)
   - Update order status to `EXPIRED` or `CANCELLED`

```python
async def reaper_job():
    """Periodic job to clean up stuck PENDING orders and restore inventory."""
    
    threshold = datetime.utcnow() - timedelta(minutes=10)
    
    # Find stuck orders
    stuck_orders = await db.fetch_all(
        """
        SELECT id, product_id, quantity 
        FROM orders 
        WHERE status = 'PENDING' AND created_at < :threshold
        FOR UPDATE SKIP LOCKED
        """,
        {"threshold": threshold}
    )
    
    for order in stuck_orders:
        # Restore inventory to Redis
        await redis.incrby(f"inventory:{order.product_id}", order.quantity)
        
        # Mark order as expired
        await db.execute(
            "UPDATE orders SET status = 'EXPIRED' WHERE id = :id",
            {"id": order.id}
        )
        
        logger.info(f"Reaped stuck order {order.id}, restored {order.quantity} units")
```

| Component | Responsibility |
|-----------|----------------|
| **Reaper Job** | Runs every 1-5 min via cron/scheduler |
| **Threshold** | Orders PENDING > 10 min are considered stuck |
| **FOR UPDATE SKIP LOCKED** | Prevents concurrent reaper instances from processing same order |
| **INCR** | Atomically restore inventory to Redis |
| **Status Update** | Mark as `EXPIRED` to prevent double-reaping |

**Why This Works:**

| Advantage | Explanation |
|-----------|-------------|
| ✅ **Simple** | No Redis keyspace notifications or TTL handlers |
| ✅ **Reliable** | Job always catches up; no missed events |
| ✅ **Debuggable** | Query DB to see all stuck orders |
| ✅ **Idempotent** | Status check prevents double-restore |
| ✅ **DB as source of truth** | No split state between Redis TTL and DB |

---

### 5. Queue Grows Faster Than Workers

**Problem:** Burst traffic overwhelms workers; queue backs up indefinitely.

**Solution: Multi-Layer Defense**

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Rate       │────▶│  Circuit    │────▶│  Queue      │────▶│  Auto-scale │
│  Limiter    │     │  Breaker    │     │  (bounded)  │     │  Workers    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

| Layer | Strategy |
|-------|----------|
| **1. Early Rejection** | Rate limit at API gateway (shed load before queue) |
| **2. Bounded Queue** | Set max queue size; reject when full |
| **3. Auto-scaling** | Scale workers based on queue depth |
| **4. Priority Lanes** | Separate queues for VIP vs regular users |
| **5. Circuit Breaker** | Trip when downstream is overwhelmed |

```python
# Bounded queue with backpressure
async def enqueue_order(order: Order):
    queue_size = await redis.llen("order_queue")
    
    if queue_size > MAX_QUEUE_SIZE:
        raise HTTPException(503, "Service temporarily unavailable")
    
    await redis.rpush("order_queue", order.json())
```

---

## 📋 Solution Summary

| Problem | Solution | Key Mechanism |
|---------|----------|---------------|
| Worker crash | Transactional Outbox + Reaper | Atomic event storage + recovery job |
| Payment retry | Idempotency Keys | Deduplicate at payment layer |
| Duplicate events | Idempotent Consumers | Event log + unique constraints |
| Leaked inventory | Periodic Reaper Job | Scan PENDING orders + restore stock |
| Queue overflow | Backpressure + Auto-scale | Shed load early, scale workers |

---

## 🔍 Why PENDING Orders Can Get "Stuck"

A **PENDING** order means:
- ✅ Inventory was reserved (Redis decremented)
- ✅ Order record exists in DB
- ❌ Payment was **not completed**

| Reason | Description |
|--------|-------------|
| **Worker crash** | Worker died after reserving inventory but before calling payment |
| **Payment timeout** | Payment gateway didn't respond in time |
| **Network issues** | Connection dropped between services |
| **Queue backlog** | Order stuck in queue too long |
| **App restart** | Deployment or crash interrupted processing |
| **User abandoned** | User closed browser during payment flow |

> 💡 This is why the **Reaper Job** is essential — it catches all these edge cases and restores inventory.

---

## 🛡️ Protection Layers Against Double Payments

When a worker crashes after payment succeeds but before updating the order status, you might worry about double-charging on retry. Here's why that **won't happen**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MULTI-LAYER PAYMENT PROTECTION                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Layer 1: Gateway Idempotency                                               │
│  ┌─────────────┐     ┌─────────────┐                                        │
│  │  Your App   │────▶│   Stripe    │  Same idempotency_key = Same result   │
│  │ key: ord123 │     │  (cached)   │  ✅ No re-charge on retry             │
│  └─────────────┘     └─────────────┘                                        │
│                                                                             │
│  Layer 2: Webhook Callback                                                  │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                    │
│  │   Stripe    │────▶│  Webhook    │────▶│  Update DB  │                    │
│  │  (success)  │     │  Endpoint   │     │  CONFIRMED  │                    │
│  └─────────────┘     └─────────────┘     └─────────────┘                    │
│                       ✅ Gateway notifies YOU of payment status             │
│                                                                             │
│  Layer 3: Order Status Guard                                                │
│  ┌─────────────────────────────────────────────────────┐                    │
│  │  if order.status != PENDING:                        │                    │
│  │      return  # Already processed, skip payment      │                    │
│  └─────────────────────────────────────────────────────┘                    │
│                       ✅ Check status before calling gateway                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Layer 1: Payment Gateway Idempotency

All major gateways support **idempotency keys** to prevent double charges:

| Gateway | Header/Field | TTL |
|---------|--------------|-----|
| **Stripe** | `Idempotency-Key` header | 24 hours |
| **PayPal** | `PayPal-Request-Id` header | 72 hours |
| **Razorpay** | `X-Razorpay-Idempotency-Key` header | 24 hours |
| **Square** | `Idempotency-Key` header | 24 hours |
| **Adyen** | `reference` field (merchant order ID) | Permanent |

```python
# Use order_id as idempotency key — deterministic and unique
await stripe.PaymentIntent.create(
    amount=1000,
    currency="usd",
    idempotency_key=f"payment_{order_id}"  # ← Same key = cached response
)
```

> 🔑 **Key Rule:** Always retry with the **SAME** idempotency key. Using a new key = new charge!

---

### Layer 2: Webhook Callbacks

Payment gateways send **webhook notifications** when payment status changes:

```
Your App                    Gateway                     Bank
   │                          │                          │
   │── Create Payment ───────▶│                          │
   │                          │── Charge ───────────────▶│
   │   (worker crashes)       │                          │
   │                          │◀─ Success ───────────────│
   │                          │                          │
   │◀── Webhook: SUCCEEDED ───│                          │
   │                          │                          │
   └── Update order status ───┘                          │
```

```python
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    event = await verify_stripe_signature(request)
    
    if event.type == "payment_intent.succeeded":
        order_id = event.data.object.metadata.order_id
        await update_order_status(order_id, OrderStatus.CONFIRMED)
    
    elif event.type == "payment_intent.payment_failed":
        order_id = event.data.object.metadata.order_id
        await update_order_status(order_id, OrderStatus.FAILED)
        await restore_inventory(order_id)  # Release reserved stock
```

> 📡 **Webhooks are your safety net** — even if your worker crashes, the gateway will notify you of the actual payment status.

---

### Layer 3: Order Status Guard

Before calling the payment gateway, **check if already processed**:

```python
async def process_order_payment(order_id: str):
    async with async_session_factory() as db:
        order = await db.get(Order, order_id)
        
        # Guard: Skip if not PENDING
        if order.status != OrderStatus.PENDING:
            logger.info(f"Order {order_id} already processed: {order.status}")
            return  # ✅ No duplicate payment attempt
        
        # Safe to proceed with payment
        result = await payment_service.process_payment(order_id)
        # ...
```

---

### Complete Protection Matrix

| Scenario | Layer 1 (Gateway) | Layer 2 (Webhook) | Layer 3 (Guard) |
|----------|-------------------|-------------------|-----------------|
| Worker crashes after payment | ✅ Cached result | ✅ Updates status | — |
| Message replayed from queue | ✅ Cached result | — | ✅ Skips payment |
| Network timeout, client retries | ✅ Same key = no re-charge | — | — |
| Concurrent duplicate requests | ✅ First wins | — | ✅ Second skips |
| Worker restarts, reprocesses | ✅ Cached result | ✅ Already updated | ✅ Skips payment |

---

### Why All Three Layers?

| Layer | Protects Against | Limitation |
|-------|------------------|------------|
| **Gateway Idempotency** | Double charging | Keys expire (24h); must track the key |
| **Webhook Callback** | Missed status updates | Webhooks can be delayed or missed |
| **Order Status Guard** | Duplicate processing | Race condition if not using DB locks |

> 🛡️ **Defense in Depth:** No single layer is perfect. Together, they provide robust protection against double payments.

---

## ⚙️ Order Worker State Machine

The order worker processes orders through a **state machine** with crash recovery at every step.

### Order Status Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORDER STATE MACHINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐     ┌─────────────────────┐     ┌───────────┐               │
│   │ PENDING  │────▶│ PAYMENT_IN_PROGRESS │────▶│ CONFIRMED │               │
│   └──────────┘     └─────────────────────┘     └───────────┘               │
│        │                    │                                               │
│        │                    │                  ┌──────────┐                 │
│        │                    └─────────────────▶│  FAILED  │                 │
│        │                                       └──────────┘                 │
│        │                                              │                     │
│        │                   ┌──────────┐               │                     │
│        └──────────────────▶│ EXPIRED  │◀──────────────┘                     │
│         (Reaper Job)       └──────────┘    (Restore Inventory)              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Worker Processing Steps

```python
# Step 1: Insert order with ON CONFLICT DO NOTHING (idempotent)
INSERT INTO orders (...) VALUES (...) ON CONFLICT (order_id) DO NOTHING

# Step 2: Transition to PAYMENT_IN_PROGRESS (guard: only if PENDING)
UPDATE orders SET status = 'PAYMENT_IN_PROGRESS' WHERE order_id = ? AND status = 'PENDING'

# Step 3: Call payment gateway with idempotency key
payment_result = await payment_service.process_payment(order_id, idempotency_key=order_id)

# Step 4: Update to final state (guard: only if PAYMENT_IN_PROGRESS)
UPDATE orders SET status = 'CONFIRMED'/'FAILED' WHERE order_id = ? AND status = 'PAYMENT_IN_PROGRESS'
```

---

### Crash Recovery at Each Step

| Crash Point | Order State | Recovery Mechanism |
|-------------|-------------|-------------------|
| After Step 1 | `PENDING` | **Reaper Job** finds stuck PENDING orders, restores inventory |
| After Step 2 (before payment call) | `PAYMENT_IN_PROGRESS` | Stuck — payment never reached gateway. **Reaper Job** must handle this state too |
| After Step 3 (payment succeeded) | `PAYMENT_IN_PROGRESS` | **Webhook** from gateway updates to `CONFIRMED` |
| After Step 3 (payment failed) | `PAYMENT_IN_PROGRESS` | **Webhook** from gateway updates to `FAILED` |
| After Step 4 | `CONFIRMED`/`FAILED` | ✅ Complete — no recovery needed |

---

### Why Intermediate State (`PAYMENT_IN_PROGRESS`)?

Without it, you can't distinguish between:

| Scenario | Status | Problem |
|----------|--------|---------|
| Order just created, payment not started | `PENDING` | Should retry payment |
| Payment call in flight | `PENDING` | Don't know if gateway received request |
| Payment completed, DB update pending | `PENDING` | Double payment risk! |

**With `PAYMENT_IN_PROGRESS`:**

| State | Meaning | Safe Action |
|-------|---------|-------------|
| `PENDING` | Payment never started | Safe to start payment |
| `PAYMENT_IN_PROGRESS` | Payment may have been sent | Wait for webhook OR query gateway |
| `CONFIRMED` / `FAILED` | Terminal state | No action needed |

---

### Idempotency Guarantees

| Operation | Idempotency Mechanism |
|-----------|----------------------|
| **Insert Order** | `ON CONFLICT (order_id) DO NOTHING` — duplicate inserts are no-op |
| **Update to PAYMENT_IN_PROGRESS** | `WHERE status = 'PENDING'` — only first update succeeds |
| **Call Payment Gateway** | `idempotency_key=order_id` — gateway returns cached result |
| **Update to CONFIRMED/FAILED** | `WHERE status = 'PAYMENT_IN_PROGRESS'` — only first update succeeds |

---

### Code Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           ORDER WORKER FLOW                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   event = await order_queue.get()                                            │
│                    │                                                         │
│                    ▼                                                         │
│   ┌────────────────────────────────────┐                                     │
│   │ INSERT ... ON CONFLICT DO NOTHING  │ ◀─── Idempotent: replay = no-op     │
│   └────────────────────────────────────┘                                     │
│                    │                                                         │
│                    ▼  💥 Crash here → PENDING (Reaper handles)               │
│   ┌────────────────────────────────────┐                                     │
│   │ UPDATE status = PAYMENT_IN_PROGRESS│                                     │
│   │ WHERE status = PENDING             │ ◀─── Guard: only PENDING orders     │
│   └────────────────────────────────────┘                                     │
│                    │                                                         │
│          ┌────────┴────────┐                                                 │
│          │ rowcount == 0?  │──── Yes ───▶ continue (already processed)       │
│          └────────┬────────┘                                                 │
│                   │ No                                                       │
│                   ▼  💥 Crash here → PAYMENT_IN_PROGRESS (stuck, needs fix)  │
│   ┌────────────────────────────────────┐                                     │
│   │ payment_service.process_payment()  │                                     │
│   │ (with idempotency_key=order_id)    │ ◀─── Gateway idempotency            │
│   └────────────────────────────────────┘                                     │
│                    │                                                         │
│                    ▼  💥 Crash here → Webhook updates status                 │
│   ┌────────────────────────────────────┐                                     │
│   │ UPDATE status = CONFIRMED/FAILED   │                                     │
│   │ WHERE status = PAYMENT_IN_PROGRESS │ ◀─── Guard: only in-progress orders │
│   └────────────────────────────────────┘                                     │
│                    │                                                         │
│          ┌────────┴────────┐                                                 │
│          │ status = FAILED │──── Yes ───▶ restore_inventory()                │
│          └────────┬────────┘                                                 │
│                   │                                                          │
│                   ▼                                                          │
│               ✅ Done                                                         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### Handling `PAYMENT_IN_PROGRESS` Stuck Orders

Orders stuck in `PAYMENT_IN_PROGRESS` need special handling:

| Scenario | Cause | Solution |
|----------|-------|----------|
| Worker crashed before calling gateway | Gateway never received request | Safe to retry payment with same idempotency key |
| Worker crashed after calling gateway | Gateway has the payment | Query gateway for status OR wait for webhook |

**Recommended: Add to Reaper Job**

```python
async def reaper_job():
    # ... existing PENDING order handling ...
    
    # Also handle stuck PAYMENT_IN_PROGRESS orders
    stuck_in_progress = await db.fetch_all(
        """
        SELECT id, order_id, product_id, flash_sale_id
        FROM orders 
        WHERE status = 'PAYMENT_IN_PROGRESS' 
        AND updated_at < :threshold
        FOR UPDATE SKIP LOCKED
        """,
        {"threshold": datetime.utcnow() - timedelta(minutes=15)}
    )
    
    for order in stuck_in_progress:
        # Option 1: Query payment gateway for actual status
        status = await payment_service.get_payment_status(order.order_id)
        
        # Option 2: If gateway has no record, safe to expire
        if status == "not_found":
            await restore_inventory(order)
            await update_order_status(order.id, OrderStatus.EXPIRED)
```