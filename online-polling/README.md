# Online Polling System

A high-performance, real-time online polling application designed to handle concurrent votes with **zero double-voting** and **eventual consistency** using CQRS pattern.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ONLINE POLLING SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐  │
│   │  Client  │────▶│   FastAPI    │────▶│  PostgreSQL  │────▶│  Redis   │  │
│   │          │     │   Backend    │     │  (Write DB)  │     │  (Cache) │  │
│   └──────────┘     └──────────────┘     └──────────────┘     └──────────┘  │
│                                                │                    ▲       │
│                                                │                    │       │
│                                                ▼                    │       │
│                                         ┌──────────────┐            │       │
│                                         │  Projection  │────────────┘       │
│                                         │   Worker     │                    │
│                                         └──────────────┘                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **One Vote Per User** | Unique constraint + idempotent operations prevent double voting |
| **Append-Only Vote Log** | Immutable audit trail for all votes |
| **CQRS Pattern** | Separate write (PostgreSQL) and read (Redis) models |
| **Atomic Operations** | Lua scripts ensure all-or-nothing vote processing |
| **Redis Cluster Safe** | Hash tags ensure all keys for a poll go to the same slot |
| **Idempotent Workers** | Re-running the same vote won't cause double counting |

---

## Architecture: CQRS Pattern

We use **Command Query Responsibility Segregation (CQRS)** to separate writes from reads:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CQRS ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   COMMAND SIDE (Writes)                  QUERY SIDE (Reads)                 │
│   ─────────────────────                  ──────────────────                 │
│                                                                             │
│   ┌─────────────┐                        ┌─────────────┐                   │
│   │  Vote API   │                        │ Results API │                   │
│   └──────┬──────┘                        └──────┬──────┘                   │
│          │                                      │                           │
│          ▼                                      ▼                           │
│   ┌─────────────┐                        ┌─────────────┐                   │
│   │ PostgreSQL  │──────────────────────▶ │    Redis    │                   │
│   │  vote_log   │    Projection Worker   │   (cache)   │                   │
│   └─────────────┘                        └─────────────┘                   │
│                                                                             │
│   • Append-only writes                   • Fast reads                       │
│   • Strong consistency                   • Eventual consistency             │
│   • Source of truth                      • Optimized for queries            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why CQRS?

| Benefit | Explanation |
|---------|-------------|
| **Scalability** | Scale reads (Redis) independently from writes (PostgreSQL) |
| **Performance** | Redis serves vote counts in O(1), no JOINs needed |
| **Flexibility** | Different data models optimized for each use case |
| **Resilience** | If Redis dies, PostgreSQL has all the data to rebuild |

---

## Database Schema

### Entity Relationships

```
Poll (1) ──────▶ (N) Option
  │
  │ (1)
  ▼
 (N)
VoteLog ◀────── User (via user_id string)
```

### Tables

**polls**
| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT | Primary key |
| question | VARCHAR(255) | Poll question |
| status | ENUM | ACTIVE / INACTIVE |
| created_at | TIMESTAMP | Creation time |

**options**
| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT | Primary key |
| poll_id | BIGINT | Foreign key to polls |
| text | VARCHAR(255) | Option text |

**vote_log** (Append-Only!)
| Column | Type | Description |
|--------|------|-------------|
| vote_id | BIGINT | Primary key |
| poll_id | BIGINT | Which poll |
| option_id | BIGINT | Which option voted for |
| user_id | VARCHAR(55) | Who voted |
| created_at | TIMESTAMP | When voted |

**Unique Constraint**: `(poll_id, user_id)` — One vote per user per poll

---

## Race Conditions & Solutions

### Race Condition 1: Double Voting

**Problem**: Two requests from the same user arrive simultaneously.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DOUBLE VOTING RACE CONDITION                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   User A (Request 1)              User A (Request 2)                        │
│   ──────────────────              ──────────────────                        │
│                                                                             │
│   Check: Has user voted?          Check: Has user voted?                    │
│         │                               │                                   │
│         ▼                               ▼                                   │
│   Result: NO                      Result: NO (race!)                        │
│         │                               │                                   │
│         ▼                               ▼                                   │
│   INSERT vote                     INSERT vote                               │
│         │                               │                                   │
│         ▼                               ▼                                   │
│   ✅ Success                      ??? Double vote?                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Solution**: PostgreSQL `ON CONFLICT DO NOTHING` + Unique Constraint

```sql
INSERT INTO vote_log (poll_id, option_id, user_id, created_at, updated_at) 
VALUES (:poll_id, :option_id, :user_id, NOW(), NOW())
ON CONFLICT (poll_id, user_id) DO NOTHING
```

| Scenario | Result |
|----------|--------|
| First vote | `rowcount = 1` (inserted) |
| Duplicate vote | `rowcount = 0` (conflict, ignored) |

The unique constraint is enforced at the **database level**, making it atomic and race-safe.

---

### Race Condition 2: Projection Worker Duplicates

**Problem**: Multiple workers read the same cursor and process the same votes.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        WORKER RACE CONDITION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Worker A                            Worker B                              │
│   ────────                            ────────                              │
│                                                                             │
│   GET cursor → 100                    GET cursor → 100 (same!)              │
│         │                                   │                               │
│         ▼                                   ▼                               │
│   Query votes > 100                   Query votes > 100                     │
│   Gets [101, 102, 103]                Gets [101, 102, 103] (same!)          │
│         │                                   │                               │
│         ▼                                   ▼                               │
│   Process vote 101                    Process vote 101                      │
│   INCR count → 42                     INCR count → 43 ❌ WRONG!             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Solution**: Idempotent Lua Script with `SISMEMBER` check

```lua
-- Check if user already in voters set (idempotency check)
local already_voted = redis.call('SISMEMBER', KEYS[1], ARGV[1])

if already_voted == 0 then
    -- Only increment if this is the first time we see this vote
    redis.call('SADD', KEYS[1], ARGV[1])
    redis.call('INCR', KEYS[2])
end

-- Always update cursor
redis.call('SET', KEYS[3], ARGV[2])

return already_voted == 0 and 1 or 0
```

| Scenario | SISMEMBER | INCR runs? | Result |
|----------|-----------|------------|--------|
| Worker A processes first | 0 (not found) | ✅ Yes | Count: 42 |
| Worker B processes same | 1 (exists!) | ❌ No | Count: 42 (unchanged) |

**The Lua script is idempotent** — running it twice for the same vote produces the same result.

---

## Lua Script Deep Dive

### Why Lua Scripts?

| Without Lua | With Lua |
|-------------|----------|
| `SISMEMBER` → network → Python | All commands |
| `SADD` → network → Python | execute as |
| `INCR` → network → Python | ONE atomic |
| `SET` → network → Python | operation |

Lua scripts execute **atomically** on the Redis server — no other client can interfere.

### The Complete Script

```lua
-- KEYS[1] = voters set:    poll:{poll_id}:voters
-- KEYS[2] = vote count:    poll:{poll_id}:option:{option_id}
-- KEYS[3] = cursor:        poll:{poll_id}:cursor

-- ARGV[1] = user_id
-- ARGV[2] = vote_id (for cursor tracking)

-- Step 1: Check if already processed (idempotency)
local already_voted = redis.call('SISMEMBER', KEYS[1], ARGV[1])

-- Step 2: Only count if new vote
if already_voted == 0 then
    redis.call('SADD', KEYS[1], ARGV[1])   -- Add to voters set
    redis.call('INCR', KEYS[2])             -- Increment option count
end

-- Step 3: Update cursor (always, even for duplicates)
redis.call('SET', KEYS[3], ARGV[2])

-- Return 1 if vote was counted, 0 if duplicate
return already_voted == 0 and 1 or 0
```

### Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LUA SCRIPT FLOW                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Input: user_id="user_x", vote_id=42, poll_id=123, option_id=5            │
│                                                                             │
│   ┌─────────────────────────────────────────┐                              │
│   │ SISMEMBER poll:{123}:voters "user_x"    │                              │
│   └─────────────────┬───────────────────────┘                              │
│                     │                                                       │
│          ┌──────────┴──────────┐                                           │
│          │                     │                                            │
│       Returns 0             Returns 1                                       │
│     (not voted)            (already voted)                                  │
│          │                     │                                            │
│          ▼                     │                                            │
│   ┌──────────────────┐        │                                            │
│   │ SADD voters set  │        │                                            │
│   │ INCR option:5    │        │                                            │
│   └────────┬─────────┘        │                                            │
│            │                   │                                            │
│            └─────────┬─────────┘                                           │
│                      │                                                      │
│                      ▼                                                      │
│           ┌──────────────────────┐                                         │
│           │ SET cursor = 42      │  ← Always runs                          │
│           └──────────────────────┘                                         │
│                      │                                                      │
│                      ▼                                                      │
│           ┌──────────────────────┐                                         │
│           │ Return 1 (new) or 0  │                                         │
│           └──────────────────────┘                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Redis Cluster Safety

### The Problem: CROSSSLOT Error

In Redis Cluster, keys are distributed across 16,384 slots. A Lua script that accesses keys in different slots will fail:

```
poll:123:voters      → Slot 5842
poll:123:option:1    → Slot 9127  ❌ CROSSSLOT ERROR!
```

### The Solution: Hash Tags

Redis only hashes the content inside `{...}`:

```
poll:{123}:voters      → Hashes only "123" → Slot 5842
poll:{123}:option:1    → Hashes only "123" → Slot 5842 ✅
poll:{123}:cursor      → Hashes only "123" → Slot 5842 ✅
```

**All keys for the same poll go to the same slot!**

### Python F-String Syntax

```python
# Triple braces: {{ = literal {, {var} = interpolate, }} = literal }
voters_key = f"poll:{{{poll_id}}}:voters"      # → "poll:{123}:voters"
option_key = f"poll:{{{poll_id}}}:option:{option_id}"  # → "poll:{123}:option:5"
```

---

## Append-Only Vote Log

### Why Append-Only?

The `vote_log` table is designed as an **immutable event log**:

| Append-Only ✅ | With Updates ❌ |
|----------------|-----------------|
| Fast sequential writes | Random I/O for updates |
| Immutable audit trail | History is modified |
| Easy replication | Update conflicts |
| Can replay from scratch | Can't replay cleanly |
| Works with CDC | Breaks CDC |

### Cursor-Based Processing

Instead of updating `vote_log` to mark processed rows, we track a **cursor** in Redis:

```python
# Get last processed vote_id from Redis
last_id = await redis_client.get("poll:{123}:cursor")  # → 42

# Query only unprocessed votes
SELECT * FROM vote_log 
WHERE poll_id = 123 AND vote_id > 42 
ORDER BY vote_id LIMIT 100
```

**Benefits**:
- Vote log stays append-only ✅
- Cursor is fast to read/write (Redis) ✅
- Can replay from any point (reset cursor to 0) ✅

---

## Projection Worker

The **Projection Worker** continuously syncs votes from PostgreSQL to Redis:

```python
class ProjectionWorker:
    async def run(self):
        while True:
            # 1. Get cursor from Redis
            last_id = await redis_client.get(CURSOR_KEY)
            
            # 2. Query new votes from PostgreSQL
            votes = await db.execute("""
                SELECT * FROM vote_log 
                WHERE vote_id > :last_id 
                LIMIT 100
            """)
            
            # 3. Process each vote with Lua script
            for vote in votes:
                await redis_client.eval(LUA_SCRIPT, ...)
            
            # 4. Sleep and repeat
            await asyncio.sleep(5)
```

### Worker Idempotency

Even if multiple workers run simultaneously, the Lua script's `SISMEMBER` check ensures votes are only counted once.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/poll` | List all polls with vote counts |
| `GET` | `/api/v1/poll/{id}` | Get poll with options |
| `POST` | `/api/v1/poll` | Create new poll |
| `POST` | `/api/v1/poll/{id}/vote` | Cast a vote |
| `GET` | `/api/v1/poll/{id}/results` | Get poll results |
| `GET` | `/api/v1/poll/{id}/check-vote/{user_id}` | Check if user voted |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI (async) |
| **Database** | PostgreSQL |
| **Cache** | Redis |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Package Manager** | uv |
| **Frontend** | Next.js + Tailwind CSS |

---

## Running the Application

### Backend

```bash
# Install dependencies
cd online-polling
uv sync

# Run the server
uv run uvicorn app.app:app --reload --port 8000

# Run projection worker (in separate terminal)
uv run python -m app.workers.redis_update_worker
```

### Frontend

```bash
cd online-polling-frontend
npm install
npm run dev
```

### Seed Data

```bash
uv run python -m app.scripts.seed_data
```

---

## Data Flow Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VOTE DATA FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   1. User votes                                                             │
│      │                                                                      │
│      ▼                                                                      │
│   2. INSERT INTO vote_log ... ON CONFLICT DO NOTHING                       │
│      │                                                                      │
│      ├── rowcount = 1 → Vote recorded ✅                                   │
│      └── rowcount = 0 → Duplicate, rejected ✅                              │
│                                                                             │
│   3. Projection Worker polls vote_log                                       │
│      │                                                                      │
│      ▼                                                                      │
│   4. Lua Script processes vote atomically                                   │
│      │                                                                      │
│      ├── SISMEMBER → user not in set → SADD + INCR                         │
│      └── SISMEMBER → user in set → Skip (idempotent)                       │
│                                                                             │
│   5. Results API reads from Redis                                           │
│      │                                                                      │
│      ▼                                                                      │
│   6. User sees vote counts (eventually consistent)                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Consistency Model

| Operation | Consistency | Why |
|-----------|-------------|-----|
| Voting | **Strong** | PostgreSQL unique constraint |
| Reading results | **Eventual** | Redis updated by worker |
| Checking if voted | **Strong** | Queries PostgreSQL directly |

### Eventual Consistency Trade-off

- **Lag**: Results may be 1-5 seconds behind actual votes
- **Benefit**: Reads are extremely fast (Redis O(1) lookups)
- **Guarantee**: No double counting, ever

---

## Future Improvements

| Improvement | Benefit |
|-------------|---------|
| **WebSocket for live updates** | Real-time result streaming |
| **Redis Sentinel/Cluster** | High availability |
| **Distributed lock for worker** | Prevent duplicate work |
| **Per-poll cursor** | Better cluster distribution |
| **Kafka/RabbitMQ for events** | Decouple worker from DB polling |

---

## License

MIT


