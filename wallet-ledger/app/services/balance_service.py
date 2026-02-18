from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.wallet_account import AccountStatus, AccountType, WalletAccount
from app.core.exceptions import InsufficientBalanceError, WalletError, WalletNotFoundError, WalletFrozenError


async def optimistic_credit(wallet_id: UUID, amount, max_retries: int, db_session: AsyncSession):
    for attempt in range(max_retries):
        # query account to get version and current_balance
        get_account_result = await db_session.execute(select(WalletAccount).where(WalletAccount.id == wallet_id))
        wallet_account = get_account_result.scalar_one_or_none()
        # validate if wallet exists and active
        if wallet_account is None:
            raise WalletNotFoundError()
        if wallet_account.status != AccountStatus.ACTIVE:
            raise WalletFrozenError()
        # update acccount with new current balance
        current_version = wallet_account.version
        new_balance = wallet_account.cached_balance + amount
        update_result = await db_session.execute(update(WalletAccount)
                                                 .where(WalletAccount.id == wallet_id)
                                                 .where(WalletAccount.version == current_version)
                                                 .values(
            version=current_version + 1,
            cached_balance=new_balance
        ))
        # check if update even happened
        if update_result.rowcount == 1:
            return new_balance, current_version + 1  # returning tuple

        # Version conflict -- someone else updated first
        # Expire the cached object so next read gets fresh data
        db_session.expire(wallet_account)

    raise WalletError("Too much contention, please retry")


async def optimistic_debit_system_account(amount, max_retries: int, db_session: AsyncSession):
    for attempt in range(max_retries):
        system_account_result = await db_session.execute(select(WalletAccount).where(WalletAccount.account_type == AccountType.SYSTEM))
        system_account = system_account_result.scalar_one_or_none()
        if system_account is None:
            raise WalletNotFoundError()
        if system_account.status != AccountStatus.ACTIVE:
            raise WalletFrozenError()
        # update acccount with new current balance
        current_version = system_account.version
        new_balance = system_account.cached_balance - amount
        update_result = await db_session.execute(update(WalletAccount)
                                                 .where(WalletAccount.id == system_account.id)
                                                 .where(WalletAccount.version == current_version)
                                                 .values(
            version=current_version + 1,
            cached_balance=new_balance
        ))
        if update_result.rowcount == 1:
            # returning tuple
            return {"new_balance": new_balance, "new_version": current_version + 1, "system_account_id": system_account.id}
        # Version conflict -- someone else updated first
        # Expire the cached object so next read gets fresh data
        db_session.expire(system_account)
    raise WalletError("Too much contention, please retry")


async def optimistic_credit_system_account(amount, max_retries: int, db_session: AsyncSession):
    for attempt in range(max_retries):
        system_account_result = await db_session.execute(select(WalletAccount).where(WalletAccount.account_type == AccountType.SYSTEM))
        system_account = system_account_result.scalar_one_or_none()
        if system_account is None:
            raise WalletNotFoundError()
        if system_account.status != AccountStatus.ACTIVE:
            raise WalletFrozenError()
        # update acccount with new current balance
        current_version = system_account.version
        new_balance = system_account.cached_balance + amount
        update_result = await db_session.execute(update(WalletAccount)
                                                 .where(WalletAccount.id == system_account.id)
                                                 .where(WalletAccount.version == current_version)
                                                 .values(
            version=current_version + 1,
            cached_balance=new_balance
        ))
        if update_result.rowcount == 1:
            # returning tuple
            return {"new_balance": new_balance, "new_version": current_version + 1, "system_account_id": system_account.id}
        # Version conflict -- someone else updated first
        # Expire the cached object so next read gets fresh data
        db_session.expire(system_account)
    raise WalletError("Too much contention, please retry")


async def optimistic_debit(wallet_id: UUID, amount, max_retries: int, db_session: AsyncSession):
    for attempt in range(max_retries):
        # query account to get version and current_balance
        get_account_result = await db_session.execute(select(WalletAccount).where(WalletAccount.id == wallet_id))
        wallet_account = get_account_result.scalar_one_or_none()
        # validate if wallet exists and active
        if wallet_account is None:
            raise WalletNotFoundError()
        if wallet_account.status != AccountStatus.ACTIVE:
            raise WalletFrozenError()
        # update acccount with new current balance
        current_version = wallet_account.version
        new_balance = wallet_account.cached_balance - amount
        update_result = await db_session.execute(update(WalletAccount)
                                                 .where(WalletAccount.id == wallet_id)
                                                 .where(WalletAccount.version == current_version)
                                                 .where(WalletAccount.cached_balance >= amount)
                                                 .values(
            version=current_version + 1,
            cached_balance=new_balance
        ))
        if update_result.rowcount == 1:
            return new_balance, current_version + 1  # returning tuple

        # rowcount == 0: either version conflict or insufficient balance
        if update_result.rowcount == 0:
            wallet = await db_session.get(WalletAccount, wallet_id)
            if wallet.cached_balance < amount:
                raise InsufficientBalanceError()

        # Version conflict -- someone else updated first
        # Expire the cached object so next read gets fresh data
        db_session.expire(wallet_account)

    raise WalletError("Too much contention, please retry")
