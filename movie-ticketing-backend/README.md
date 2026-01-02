# Movie Ticketing Backend

A high-performance movie ticket booking system designed to handle concurrent seat reservations with **zero double-booking**.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MOVIE TICKETING SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐  │
│   │  Client  │────▶│   FastAPI    │────▶│    Redis     │────▶│ PostgreSQL│ │
│   │          │     │   Backend    │     │  (Locks)     │     │   (Data)  │ │
│   └──────────┘     └──────────────┘     └──────────────┘     └──────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Atomic Seat Locking** | Redis Lua scripts ensure all-or-nothing seat reservation |
| **Distributed Locking** | Prevents double-booking across multiple server instances |
| **Redis Cluster Safe** | Hash tags ensure all keys for a show go to the same slot |
| **Pessimistic Locking** | `FOR UPDATE` on booking confirmation prevents race conditions |
| **Idempotent Confirm API** | Same request = same response (no duplicate confirmations) |
| **TTL-based Lock Expiry** | Abandoned bookings auto-release seats after 10 minutes |

---

## Booking Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BOOKING FLOW                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Step 1: Lock Seats                                                        │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│   │ Check DB    │────▶│ Redis Lua   │────▶│ Create      │                   │
│   │ Availability│     │ Atomic Lock │     │ Booking     │                   │
│   └─────────────┘     └─────────────┘     └─────────────┘                   │
│         │                   │                   │                           │
│         │                   │                   ▼                           │
│         │                   │          Status: INITIATED                    │
│         │                   │                                               │
│   Step 2: Confirm (within TTL)                                              │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│   │ Idempotency │────▶│ FOR UPDATE  │────▶│ Update      │                   │
│   │ Check       │     │ Lock        │     │ ShowSeats   │                   │
│   └─────────────┘     └─────────────┘     └─────────────┘                   │
│                                                 │                           │
│                                                 ▼                           │
│                                        Status: CONFIRMED                    │
│                                        ShowSeat: BOOKED                     │
│                                                                             │
│   Alternative: TTL Expires                                                  │
│   ┌─────────────┐                                                           │
│   │ Redis Locks │───▶ Auto-deleted after 600s                               │
│   │ Expire      │     Seats become available again                          │
│   └─────────────┘                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Concurrency Handling

### Problem: Double Booking

When 10 users try to book the same seats simultaneously:

```
User A: Check seats → Available → Lock → ✅ Success
User B: Check seats → Available → Lock → ??? (race condition!)
```

### Solution: Redis Lua Atomic Script

```lua
-- All-or-nothing seat locking
-- Step 1: Check ALL seats first
for i = 4, #ARGV do
    local lock_key = key_prefix .. ":seat:" .. ARGV[i]
    if redis.call('EXISTS', lock_key) == 1 then
        return 0  -- Abort if ANY seat is locked
    end
end

-- Step 2: Lock ALL seats atomically
for i = 4, #ARGV do
    local lock_key = key_prefix .. ":seat:" .. ARGV[i]
    redis.call('SET', lock_key, booking_id, 'EX', ttl, 'NX')
end
return 1  -- Success
```

### Why This Works

| Guarantee | Mechanism |
|-----------|-----------|
| **Atomicity** | Lua script executes as single operation |
| **No partial locks** | Either all seats lock or none do |
| **No race condition** | Other clients block until script completes |
| **Auto-cleanup** | TTL ensures abandoned locks expire |

---

## Redis Cluster Safety

### The Problem

In Redis Cluster, keys are distributed across slots. A Lua script that accesses keys in different slots will fail with `CROSSSLOT` error.

### The Solution: Hash Tags

```
# Without hash tags (BROKEN in cluster)
lock:show:123:seat:1  → Slot 4523
lock:show:123:seat:2  → Slot 8891  ❌ CROSSSLOT ERROR

# With hash tags (WORKS in cluster)
lock:{show:123}:seat:1  → Slot 7842
lock:{show:123}:seat:2  → Slot 7842  ✅ Same slot!
```

Redis hashes only the content inside `{...}`, so all seats for the same show go to the same slot.

---

## Idempotency

### Confirm Booking API

```python
@router.post("/booking/{booking_id}/confirm")
async def confirm_booking(booking_id: int, request: Request):
    idem_key, cached, is_repeat = await check_idempotency(request, redis)
    if is_repeat:
        return cached  # Return cached response
    
    result = await crud_booking.confirm_booking(db, booking_id, idem_key, redis)
    # Cache response for future duplicate requests
    await redis.set(f"idempotency:{idem_key}", result, ex=600)
    return result
```

| Request | Action |
|---------|--------|
| First request | Process and cache response |
| Duplicate request | Return cached response |

---

## Database Design

### Entity Relationships

```
Theatre (1) ──────▶ (N) Screen (1) ──────▶ (N) Seat
                         │
                         │ (1)
                         ▼
                        (N)
Movie (1) ──────▶ (N) Show (1) ──────▶ (N) ShowSeat ◀────── (1) Seat
                         │
                         │ (1)
                         ▼
                        (N)
                    Booking (1) ──────▶ (N) BookingSeat
```

### Key Tables

| Table | Purpose |
|-------|---------|
| `ShowSeat` | Junction table: seat availability per show |
| `Booking` | Tracks booking status (INITIATED → CONFIRMED) |
| `BookingSeat` | Links booking to specific seats |

---

## Booking Statuses

| Status | Meaning |
|--------|---------|
| `INITIATED` | Seats locked in Redis, awaiting payment |
| `CONFIRMED` | Payment done, seats permanently booked |
| `CANCELLED` | User cancelled the booking |
| `EXPIRED` | Lock expired before confirmation |

### ShowSeat Statuses

| Status | Meaning |
|--------|---------|
| `AVAILABLE` | Seat is free to book |
| `LOCKED` | Temporarily held (Redis lock) |
| `BOOKED` | Permanently reserved |
| `UNAVAILABLE` | Seat not for sale (maintenance, etc.) |

---

## CAP Theorem Analysis

### What is CAP?

| Property | Definition |
|----------|------------|
| **C**onsistency | Every read receives the most recent write |
| **A**vailability | Every request receives a response |
| **P**artition Tolerance | System works despite network failures |

> In distributed systems, you can only have **2 out of 3**.

---

### Our Choice: **CP (Consistency + Partition Tolerance)**

For movie ticketing, **we choose Consistency over Availability**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CAP TRADE-OFF                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                           C                                                 │
│                          /│\                                                │
│                         / │ \                                               │
│                        /  │  \                                              │
│                       /   │   \                                             │
│                      / ✅ │    \                                            │
│                     /  CP │     \                                           │
│                    /      │      \                                          │
│                   /       │       \                                         │
│                  A────────┴────────P                                        │
│                                                                             │
│   We sacrifice some Availability to guarantee Consistency                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Why Consistency Matters for Ticketing

| Scenario | Consistency Priority | Availability Priority |
|----------|---------------------|----------------------|
| Two users book same seat | ✅ One succeeds, one fails | ❌ Both "succeed" → oversell |
| Network partition | ✅ Reject bookings until resolved | ❌ Accept all → conflicts |
| Redis unavailable | ✅ Reject new bookings | ❌ Allow without locks → chaos |

---

## ⚠️ What Happens If We Choose Availability Over Consistency?

If we prioritize **Availability (AP)** instead of **Consistency (CP)**, here are the consequences:

### Scenario 1: Double Booking (Overselling)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AVAILABILITY OVER CONSISTENCY                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   User A (Server 1)              User B (Server 2)                          │
│   ──────────────────             ──────────────────                         │
│   Check seat A5 → AVAILABLE      Check seat A5 → AVAILABLE                  │
│         │                              │                                    │
│         │     (Network Partition)      │                                    │
│         │     Servers can't sync       │                                    │
│         ▼                              ▼                                    │
│   Book seat A5 → ✅ SUCCESS      Book seat A5 → ✅ SUCCESS                  │
│                                                                             │
│   💥 RESULT: Both users "own" seat A5                                       │
│   💥 One user shows up and has no seat!                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Scenario 2: Conflict Resolution Nightmare

If we allow both bookings to succeed, we need conflict resolution:

| Resolution Strategy | Problem |
|--------------------|---------|
| **Last Write Wins** | User A's valid booking silently deleted |
| **First Write Wins** | User B's confirmation is invalid |
| **Manual Resolution** | Customer support nightmare, refunds, compensation |
| **Random Winner** | Both users angry, both may leave |

### Scenario 3: Customer Experience Disaster

```
Timeline of an AP System Failure:

1. User books seat A5                 → "Booking Confirmed! ✅"
2. User receives email confirmation   → "Your seats are reserved!"
3. User pays for tickets              → $50 charged
4. User arrives at theatre            → "Sorry, seat A5 is occupied"
5. User demands refund                → Refund + $20 compensation
6. User leaves 1-star review          → "NEVER BOOKING HERE AGAIN"

Cost: $70 + reputation damage + lost customer
```

---

## Consequences Summary: AP vs CP

| Aspect | CP (Our Choice) | AP (Alternative) |
|--------|-----------------|------------------|
| **User Experience** | "Seat unavailable, try another" | "Confirmed!" then "Sorry, oversold" |
| **Trust** | Users trust confirmations | Users doubt every confirmation |
| **Operations** | Simple, predictable | Complex conflict resolution |
| **Cost** | Some lost sales | Refunds + compensation + lawsuits |
| **Reputation** | Reliable system | "They oversell tickets" |

---

## When AP Might Be Acceptable

| System | Why AP Works |
|--------|--------------|
| **Social Media Likes** | Duplicate likes are harmless; eventually consistent |
| **Shopping Cart** | Can show "out of stock" at checkout |
| **Content Delivery** | Stale content is acceptable |
| **Logging Systems** | Missing a log entry is not catastrophic |

---

## When CP Is Mandatory

| System | Why CP Is Required |
|--------|-------------------|
| **Ticketing** | One seat = one person, physically |
| **Banking** | Money must balance, no overdrafts |
| **Inventory** | Can't sell what you don't have |
| **Healthcare** | Patient records must be accurate |

---

## Our Consistency Guarantees

| Guarantee | Implementation |
|-----------|----------------|
| **No Double Booking** | Redis Lua atomic locks |
| **No Phantom Reads** | Pessimistic locking (`FOR UPDATE`) |
| **No Lost Updates** | Database transactions |
| **Idempotent Confirms** | Idempotency key + cached responses |

---

## Trade-offs We Accept

| Sacrifice | Why We Accept It |
|-----------|------------------|
| **Temporary Unavailability** | Better than overselling |
| **Slower Responses** | Lock acquisition takes time |
| **Reduced Throughput** | Serialized access to hot seats |
| **Redis Dependency** | Single point of failure (mitigate with Sentinel/Cluster) |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/booking/seats/{show_id}/lock` | Lock seats for booking |
| `POST` | `/booking/booking/{booking_id}/confirm` | Confirm booking (idempotent) |
| `GET` | `/shows/{show_id}` | Get show details |
| `GET` | `/shows/{show_id}/seats` | Get seat availability |

---

## Running the Application

```bash
# Install dependencies
uv sync

# Run the server
uv run uvicorn main:app --reload

# Run tests
uv run pytest
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI |
| **Database** | PostgreSQL |
| **Cache/Locks** | Redis |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Package Manager** | uv |

---

## Future Improvements

| Improvement | Benefit |
|-------------|---------|
| **Redis Sentinel** | High availability for Redis |
| **Read Replicas** | Scale read operations |
| **Event Sourcing** | Audit trail for all bookings |
| **Queue-based Booking** | Handle burst traffic |
| **Seat Release Job** | Clean up expired INITIATED bookings |

