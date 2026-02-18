# Wallet Ledger - Architecture Document

## 1. System Overview

A **closed-loop wallet ledger** built with FastAPI, SQLAlchemy (async), and PostgreSQL. "Closed-loop" means money stays within the platform ecosystem -- users load money in, spend it within the platform, and withdraw it out. Think Paytm or PhonePe wallet.

The system uses **double-entry bookkeeping**, the same accounting principle used by banks: every transaction produces exactly two ledger entries (a debit and a credit), ensuring the books always balance. The sum of all account balances across the entire system is always zero.

### Tech Stack

- **FastAPI** -- async HTTP framework
- **SQLAlchemy 2.0** -- async ORM with `asyncpg` driver
- **PostgreSQL** -- primary database
- **Pydantic v2** -- request/response validation
- **Alembic** -- database migration management (async mode with `greenlet`)

---

## 2. Data Model

### 2.1 WalletAccount

Represents a wallet. Each user/merchant has one. There is also one platform-wide SYSTEM account.

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `user_id` | String (unique) | Owner identifier |
| `account_type` | Enum: USER_ACCOUNT, MERCHANT_ACCOUNT, SYSTEM | Determines locking strategy and role |
| `status` | Enum: ACTIVE, FROZEN, CLOSED | Only ACTIVE accounts can transact |
| `cached_balance` | BigInteger | Denormalized balance in smallest currency unit (paise/cents). Source of truth is the ledger, this is a cache for fast reads |
| `version` | Integer | Used for optimistic locking on high-traffic accounts |
| `created_at` | DateTime | Timestamp |
| `updated_at` | DateTime | Timestamp |

**Why BigInteger for balance?** Floating-point math causes rounding errors (`0.1 + 0.2 != 0.3`). All amounts are stored as integers in the smallest currency unit (paise for INR, cents for USD). 500 means 5.00 INR.

### 2.2 Transaction

Represents a high-level operation (credit, debit, transfer, refund). One transaction produces exactly two ledger entries.

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `source_account_id` | UUID (FK -> wallet_accounts) | Where money comes from |
| `destination_account_id` | UUID (FK -> wallet_accounts) | Where money goes to |
| `transaction_type` | Enum: CREDIT, DEBIT, TRANSFER, REFUND | What kind of operation |
| `idempotency_key` | String (unique) | Client-provided key to prevent duplicate processing |
| `amount` | BigInteger | Transaction amount in smallest currency unit |
| `status` | Enum: PENDING, COMPLETED, FAILED | Transaction state |
| `created_at` | DateTime | Timestamp |

### 2.3 LedgerEntry

The append-only accounting record. Each entry belongs to one account and one transaction. Ledger entries are **immutable** -- they are never updated or deleted. To reverse a transaction, you create new correcting entries (refund).

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `account_id` | UUID (FK -> wallet_accounts) | Which account's book this entry belongs to |
| `transaction_id` | UUID (FK -> transactions) | Links the two entries of a double-entry pair |
| `amount` | BigInteger | Always positive -- direction is determined by entry_type |
| `entry_type` | Enum: DEBIT, CREDIT | Money leaving (DEBIT) or entering (CREDIT) the account |
| `running_balance` | BigInteger | Account balance after this entry -- useful for auditing |
| `created_at` | DateTime | Timestamp (no updated_at -- entries are immutable) |

**Why `account_id` on LedgerEntry when Transaction already has source/destination?**
A Transaction knows both accounts. But a LedgerEntry is a line in a **specific account's** book. To query "show me all entries for merchant X" or "compute merchant X's balance", you need `account_id` directly on the entry. Without it, you'd need complex joins to figure out which side of each transaction the merchant was on.

### 2.4 IdempotencyKey

Stores processed request keys and their cached responses to prevent duplicate processing.

| Column | Type | Purpose |
|--------|------|---------|
| `key` | String | Primary key -- the client-provided idempotency key |
| `request_hash` | String | SHA-256 hash of the request body. Used to detect key reuse with different payloads |
| `request_json` | JSONB | Cached response to return on replay |
| `created_at` | DateTime | Timestamp |
| `updated_at` | DateTime | Timestamp |

### 2.5 Entity Relationships

```
WalletAccount (1) ──── (many) LedgerEntry
Transaction   (1) ──── (2)    LedgerEntry   (always exactly 2 per transaction)
WalletAccount (1) ──── (many) Transaction   (as source or destination)
```

---

## 3. Double-Entry Bookkeeping

### The Rule

Every transaction creates exactly **two** ledger entries: one DEBIT and one CREDIT. The sum of all accounts in the system is always zero.

### Credit (Load Money)

User loads 500 into their wallet. Money enters the platform from the outside world.

```
Transaction: type=CREDIT, source=SYSTEM, destination=UserWallet, amount=500

LedgerEntry 1: account=SYSTEM,     entry_type=DEBIT,  amount=500, running_balance=-500
LedgerEntry 2: account=UserWallet,  entry_type=CREDIT, amount=500, running_balance=+500

System total: -500 + 500 = 0
```

### Debit (Withdraw Money)

User withdraws 200 from their wallet. Money leaves the platform.

```
Transaction: type=DEBIT, source=UserWallet, destination=SYSTEM, amount=200

LedgerEntry 1: account=UserWallet,  entry_type=DEBIT,  amount=200, running_balance=+300
LedgerEntry 2: account=SYSTEM,      entry_type=CREDIT, amount=200, running_balance=-300

System total: -300 + 300 = 0
```

### Transfer (Wallet to Wallet)

User A pays Merchant X 150. Money stays inside the platform -- SYSTEM account is NOT involved.

```
Transaction: type=TRANSFER, source=UserA, destination=MerchantX, amount=150

LedgerEntry 1: account=UserA,     entry_type=DEBIT,  amount=150, running_balance=+150
LedgerEntry 2: account=MerchantX, entry_type=CREDIT, amount=150, running_balance=+150

System total: unchanged (money moved internally)
```

### Refund

Reverse of a transfer. Merchant X refunds User A 150.

```
Transaction: type=REFUND, source=MerchantX, destination=UserA, amount=150

LedgerEntry 1: account=MerchantX, entry_type=DEBIT,  amount=150
LedgerEntry 2: account=UserA,     entry_type=CREDIT, amount=150
```

---

## 4. SYSTEM Account

There is exactly **one** SYSTEM account for the entire platform. It represents the boundary between the wallet ecosystem and the outside world.

- Created once at startup with `account_type=SYSTEM`
- Balance starts at 0
- Goes **negative** as users load money (this is expected -- it represents total money the platform holds on behalf of users)
- `abs(SYSTEM.cached_balance)` = total money held by the platform

### Money Flow

```
Outside world <---> SYSTEM account <---> User/Merchant wallets

Load money:    SYSTEM --> User         (SYSTEM goes more negative)
Withdraw:      User   --> SYSTEM       (SYSTEM goes less negative)
Pay merchant:  User   --> Merchant     (SYSTEM not involved)
Transfer:      User A --> User B       (SYSTEM not involved)
```

### Reconciliation Check

At any point: `SUM(all wallet cached_balances) = 0`. If not zero, there is a bug.

---

## 5. Concurrency Challenges & Solutions

### 5.1 Double Deductions (Race Condition)

**Problem:** Two concurrent debits read the same balance (e.g., 500). Both pass the balance check, both deduct. User ends up with a negative balance.

**Solution: Pessimistic Locking (`SELECT FOR UPDATE`)**

```sql
SELECT * FROM wallet_accounts WHERE id = :id FOR UPDATE
-- Row is now locked. Other transactions trying to lock the same row WAIT here.
-- Check balance, deduct, commit.
-- Lock released on COMMIT.
```

In SQLAlchemy:

```python
result = await session.execute(
    select(WalletAccount)
    .where(WalletAccount.id == wallet_id)
    .with_for_update()
)
```

The second concurrent request waits until the first commits. It then reads the updated balance and correctly rejects if insufficient.

### 5.2 Duplicate Transactions (Network Retries)

**Problem:** Client sends a payment request, gets a timeout, retries with the same intent. Server processes it twice -- user charged twice.

**Solution: Idempotency Keys**

Every mutating request includes an `Idempotency-Key` header. Before processing:

1. Check if key exists in `idempotency_keys` table
2. If exists AND `request_hash` matches: return cached response (safe replay)
3. If exists AND `request_hash` differs: return 409 Conflict (same key, different request body -- client bug)
4. If not exists: process the request, then store the key + response

The `request_hash` is a SHA-256 of the JSON-serialized request body (with `sort_keys=True` for deterministic ordering). This detects the edge case where a client accidentally reuses a key for a different operation.

### 5.3 Partial Failures (Inconsistent State)

**Problem:** In a credit operation, the Transaction record is inserted but the LedgerEntry insertion fails. Now the transaction exists without matching ledger entries -- the books don't balance.

**Solution: Single Database Transaction**

All steps of an operation are wrapped in `async with db_session.begin()`:

```python
async with db_session.begin():
    # 1. Check idempotency
    # 2. Lock wallet
    # 3. Create Transaction (flush to get ID)
    # 4. Create 2 LedgerEntries
    # 5. Update cached_balance
    # 6. Save idempotency record
# Auto-commits here on success.
# Auto-rolls back if ANY step raises an exception.
```

If anything fails at any step, everything rolls back. All or nothing.

### 5.4 Deadlocks in Transfers

**Problem:** Two concurrent transfers between the same two wallets:
- Request A: Transfer from Wallet_1 to Wallet_2 -- locks Wallet_1, then tries to lock Wallet_2
- Request B: Transfer from Wallet_2 to Wallet_1 -- locks Wallet_2, then tries to lock Wallet_1
- Both hold one lock and wait for the other -- **deadlock**.

**Solution: Always lock in consistent order (by wallet ID)**

```python
first_id = min(source_wallet.id, dest_wallet.id)
second_id = max(source_wallet.id, dest_wallet.id)

await session.execute(select(...).where(id == first_id).with_for_update())
await session.execute(select(...).where(id == second_id).with_for_update())
```

Both Request A and Request B lock Wallet_1 first (smaller ID). Request B waits for A to finish. No cycle, no deadlock. This works because deadlocks require a circular wait -- if everyone acquires locks in the same global order, cycles are impossible.

### 5.5 Hot Accounts (High-Concurrency Merchant)

**Problem:** A popular merchant receives thousands of payments per second. `SELECT FOR UPDATE` serializes all transactions on that row -- each waits for the previous one to commit (50-100ms lock hold time). Throughput collapses.

**Solution: Optimistic Locking with Version Column**

Instead of locking the row upfront, attempt an atomic UPDATE with a version check:

```sql
UPDATE wallet_accounts
SET cached_balance = cached_balance + :amount,
    version = version + 1
WHERE id = :wallet_id
  AND version = :current_version
```

- If `rowcount == 1`: success, version matched, update applied
- If `rowcount == 0`: someone else updated first (version changed). Re-read and retry (up to 3 attempts)

**Why this is faster:** The row lock is held only for the duration of the UPDATE statement (microseconds), not the entire transaction (milliseconds). Concurrent requests don't block each other -- they just retry on conflict.

**Strategy selection by account type:**

| Account Type | Locking Strategy | Why |
|---|---|---|
| USER_ACCOUNT | Pessimistic (`FOR UPDATE`) | Low traffic, simple and safe |
| MERCHANT_ACCOUNT | Optimistic (version column) | High traffic, needs throughput |
| SYSTEM | Optimistic (version column) | Every credit/debit touches it -- it's a hot account |

### 5.6 Overdraft Protection

**Problem:** Balance must never go below zero.

**Solution for pessimistic path:** Check `cached_balance >= amount` after acquiring the lock, before deducting.

**Solution for optimistic path:** Include the check in the WHERE clause of the atomic UPDATE:

```sql
UPDATE wallet_accounts
SET cached_balance = cached_balance - :amount, version = version + 1
WHERE id = :id AND version = :v AND cached_balance >= :amount
```

If balance is insufficient, `rowcount == 0`. Re-read to distinguish "insufficient balance" from "version conflict".

### 5.7 Foreign Key Performance

**Concern:** With high insert rates on `ledger_entries`, does the FK to `wallet_accounts.id` cause lock contention on the parent row?

**Answer: No.** PostgreSQL uses `FOR KEY SHARE` (weakest row-level lock) when inserting a child row. This only conflicts with `FOR KEY UPDATE` (modifying the parent's primary key) or `DELETE`. It does NOT conflict with:
- Normal updates to non-key columns (`cached_balance`, `version`) -- these take `FOR NO KEY UPDATE`
- Other child inserts -- these also take `FOR KEY SHARE`

So thousands of concurrent ledger entry inserts referencing the same wallet row cause zero contention with each other or with balance updates.

---

## 6. API Endpoints

All mutating endpoints require an `Idempotency-Key` header.

| Method | Path | Purpose | Idempotency Required |
|--------|------|---------|---------------------|
| POST | `/api/v1/wallets/` | Create a new wallet | No |
| GET | `/api/v1/wallets/{wallet_id}` | Get wallet details | No |
| GET | `/api/v1/wallets/{wallet_id}/balance` | Get wallet balance | No |
| POST | `/api/v1/wallets/{wallet_id}/credit` | Load money into wallet | Yes |
| POST | `/api/v1/wallets/{wallet_id}/debit` | Withdraw money from wallet | Yes |
| POST | `/api/v1/wallets/transfer` | Transfer between wallets | Yes |

---

## 7. Project Structure

```
wallet-ledger/
  app/
    api/
      routes_wallet.py          # All wallet/transaction endpoints
      routes_health.py          # Health check
    core/
      config.py                 # Settings (DATABASE_URL, APP_NAME)
      exceptions.py             # WalletError, InsufficientBalanceError, etc.
    db/
      base.py                   # SQLAlchemy DeclarativeBase
      core.py                   # Engine, session factory, init_db
    models/
      __init__.py               # Re-exports all models (ensures table creation)
      wallet_account.py         # WalletAccount + AccountType/AccountStatus enums
      transaction.py            # Transaction + TransactionType/TransactionStatus enums
      ledger_entry.py           # LedgerEntry + EntryType enum
      idempotency_key.py        # IdempotencyKey
      mixins/
        timestamp.py            # TimestampMixin (created_at, updated_at)
    schemas/
      wallet.py                 # Pydantic: CreateWalletRequest, WalletResponse, BalanceResponse
      transaction.py            # Pydantic: CreditRequest, DebitRequest, TransferRequest, TransactionResponse
    crud/
      wallet_service.py         # Business logic: credit, debit, transfer (pessimistic + optimistic)
    services/
      idempotency_service.py    # check_idempotency, save_idempotency, compute_request_hash
      balance_service.py        # optimistic_credit, optimistic_debit, optimistic_*_system_account
  migrations/
    env.py                       # Alembic environment -- connects to DB, imports models
    script.py.mako               # Template for new migration files
    versions/                    # Auto-generated migration scripts live here
      xxxx_initial_schema.py
  alembic.ini                    # Alembic config (DB URL, migration path, logging)
  main.py                        # Uvicorn entry point
  pyproject.toml                 # Dependencies
```

---

## 8. Database Migrations (Alembic)

### Why Not `create_all()`?

Initially, tables were created at startup using `Base.metadata.create_all()`. This works for bootstrapping but is dangerous beyond early development:

- `create_all()` only creates tables that **don't exist yet**. It cannot alter existing tables (add columns, change types, add indexes).
- If you add a `phone_number` column to `WalletAccount` in Python, the existing database table stays unchanged -- no error, no warning, just silent inconsistency.
- No history of what changed, when, or why. No way to roll back.

Alembic solves all of this with **version-controlled migration scripts**.

### How Alembic Works

```
SQLAlchemy Models  ──autogenerate──>  Migration File  ──upgrade──>  PostgreSQL
   (Python code)                     (upgrade/downgrade)            (actual tables)
```

1. You change a model in Python (e.g., add a column)
2. `alembic revision --autogenerate` compares your models against the live database and generates a migration file with the diff
3. `alembic upgrade head` executes the migration's `upgrade()` function against the database
4. Alembic records the revision ID in an `alembic_version` table so it knows what has been applied

Each migration file has two functions:
- `upgrade()` -- apply the change (e.g., `ALTER TABLE ADD COLUMN`)
- `downgrade()` -- reverse the change (e.g., `ALTER TABLE DROP COLUMN`)

### Key Files

**`alembic.ini`** -- Top-level config. The most important setting is `sqlalchemy.url`, but we leave it blank and provide the URL from Python code instead (so it reads from our `settings.DATABASE_URL`, keeping the single source of truth).

**`migrations/env.py`** -- The script Alembic runs to connect to the database and execute migrations. Our customizations:

```python
from app.db.base import Base
from app.models import WalletAccount, LedgerEntry, IdempotencyKey, Transaction
from app.core.config import settings

target_metadata = Base.metadata   # Alembic compares this against the live DB

def get_url():
    return settings.DATABASE_URL  # postgresql+asyncpg://...
```

`target_metadata` tells Alembic what the schema **should** look like. `get_url()` tells it which database to compare against. The `--autogenerate` flag diffs the two and produces migration scripts.

**`migrations/versions/`** -- Where migration files live. Each file is named `{revision_id}_{slug}.py` and contains an `upgrade()` and `downgrade()` function. These files are committed to git.

### Setup Notes (Async)

Alembic was designed for synchronous SQLAlchemy. For async (`asyncpg`), two extra things are needed:

1. **`alembic init -t async migrations`** -- the `-t async` flag generates an `env.py` that uses `async_engine_from_config` and `asyncio.run()` instead of synchronous engine creation.

2. **`greenlet` package** -- SQLAlchemy's `connection.run_sync()` (used in `env.py` to bridge async engine with sync migration runner) requires `greenlet` under the hood. Without it: `ValueError: the greenlet library is required`.

### Common Commands

```bash
# Generate a migration by comparing models vs database
uv run alembic revision --autogenerate -m "description of change"

# Apply all pending migrations
uv run alembic upgrade head

# Roll back the last migration
uv run alembic downgrade -1

# See current database revision
uv run alembic current

# See migration history
uv run alembic history

# See what SQL a migration would run (without executing)
uv run alembic upgrade head --sql
```

### Day-to-Day Workflow

```
1. Edit a model         (e.g., add `phone: str` to WalletAccount)
2. Generate migration   (alembic revision --autogenerate -m "add phone to wallet")
3. Review the file      (ALWAYS review -- autogenerate can miss things or get them wrong)
4. Apply                (alembic upgrade head)
5. Commit to git        (migration file + model change together)
```

### Gotchas Learned

| Issue | What Happened | Why |
|-------|---------------|-----|
| `No module named 'psycopg2'` | `alembic.ini` had `postgresql://` as the URL | `postgresql://` uses psycopg2 (sync driver). Need `postgresql+asyncpg://` for our async setup. Fix: provide URL from `get_url()` instead of ini file |
| `No module named 'greenlet'` | Ran `alembic revision --autogenerate` | Alembic's async `env.py` uses `run_sync()` which needs `greenlet`. Fix: `uv add greenlet` |
| `Target database is not up to date` | Ran `revision --autogenerate` twice | A pending migration exists that hasn't been applied. Fix: run `alembic upgrade head` first, then generate new migrations |
| Empty migration (`pass`) | Ran autogenerate with tables already created by `create_all()` | Alembic compared models against existing tables, found no diff. Fix: drop tables first, then generate, or use `alembic stamp head` to adopt existing schema |
| `target_metadata = None` | Autogenerate produced empty migration | The auto-generated `env.py` template has `target_metadata = None`. Must set it to `Base.metadata` so Alembic knows the target schema |

---

## 9. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Amounts as BigInteger (paise/cents) | Avoids floating-point rounding errors in financial math |
| Append-only ledger entries | Accounting principle: never edit history, add correcting entries instead |
| `cached_balance` on WalletAccount | Avoids computing `SUM(ledger_entries)` on every balance check. Reconciliation verifies cache matches ledger |
| `running_balance` on LedgerEntry | Allows point-in-time balance verification without summing from the beginning |
| `version` column on WalletAccount | Enables optimistic locking for high-traffic accounts without row-level locks |
| Idempotency key as separate table | Decouples retry logic from transaction logic. Response caching enables safe replays |
| SYSTEM account for money in/out | Ensures double-entry books always balance. `SUM(all accounts) = 0` is the invariant |
| `async with session.begin()` | Single transaction boundary. Auto-commit on success, auto-rollback on failure |
| Alembic over `create_all()` | Version-controlled migrations that can alter tables, track history, and roll back. `create_all()` can only create new tables |
| DB URL from Python, not ini | `alembic.ini` URL left blank; `env.py` reads from `settings.DATABASE_URL`. Single source of truth for connection config |
