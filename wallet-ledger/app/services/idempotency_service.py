import hashlib
import json
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.idempotency_key import IdempotencyKey
from app.core.exceptions import WalletError


def compute_request_hash(request_data: dict) -> str:
    serialized = json.dumps(request_data, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


async def check_idempotency(idempotency_key: str, request_hash: str, db_session: AsyncSession):
    try:
        get_idempotency_key = await db_session.execute(select(IdempotencyKey).where(IdempotencyKey.key == idempotency_key))
        idempotency_row = get_idempotency_key.scalar_one_or_none()
        if idempotency_row is None:
            return None
        if idempotency_row.request_hash != request_hash:
            raise WalletError(
                "Idempotency key conflict: request hash mismatch")
        return idempotency_row.request_json
    except Exception as e:
        logging.error(f"failed to check idempotency: {e}", exc_info=True)
        raise WalletError("failed to check idempotency")


async def save_idempotency(idempotency_key: str, request_hash: str, request_json: dict, db_session: AsyncSession):
    try:
        idempotency_key_row = IdempotencyKey(
            key=idempotency_key,
            request_hash=request_hash,
            request_json=request_json,
        )
        db_session.add(idempotency_key_row)
        await db_session.commit()
        return idempotency_key_row
    except Exception as e:
        logging.error(f"failed to save idempotency: {e}", exc_info=True)
        raise WalletError("failed to save idempotency")
