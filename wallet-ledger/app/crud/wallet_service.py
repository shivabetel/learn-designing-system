import logging
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.wallet import CreateWalletRequest
from app.schemas.transaction import CreditRequest, DebitRequest, TransferRequest
from app.models.wallet_account import AccountStatus, AccountType, WalletAccount
from app.models.idempotency_key import IdempotencyKey
from app.core.exceptions import InsufficientBalanceError, WalletError, WalletNotFoundError, WalletFrozenError
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.ledger_entry import EntryType, LedgerEntry
from app.services.idempotency_service import check_idempotency, save_idempotency, compute_request_hash


class WalletCrudService:
    async def get_wallet(self, walletId: UUID, db_session: AsyncSession):
        try:
            result = await db_session.execute(select(WalletAccount).where(WalletAccount.id == walletId))
            wallet = result.scalar_one_or_none()
            if wallet is None:
                raise WalletNotFoundError()
            return wallet
        except Exception as e:
            # how to check if e is instance of WalletNotFoundError?
            logging.error(f"Failed to get wallet: {e}", exc_info=True)
            if isinstance(e, WalletNotFoundError):
                raise e
            raise WalletError(f"Failed to get wallet")

    async def create_wallet(self, db_session: AsyncSession, data: CreateWalletRequest):
        try:
            wallet = WalletAccount(
                user_id=data.user_id,
                account_type=data.account_type,
            )
            db_session.add(wallet)
            await db_session.commit()
            await db_session.refresh(wallet)
            return wallet
        except Exception as e:
            # how to add logging here?
            logging.error(f"Failed to create wallet: {e}", exc_info=True)
            await db_session.rollback()
            raise WalletError(f"Failed to create wallet")

    async def get_balance(self, walletId: UUID, db_session: AsyncSession):
        try:
            result = await self.get_wallet(walletId=walletId, db_session=db_session)
            return result.cached_balance
        except Exception as e:
            logging.error(
                f"failed to get balance becuase of {e}", exc_info=True)
            if isinstance(e, WalletNotFoundError):
                raise e
            raise WalletError("failed to get balance")
        pass

    async def credit_wallet(self, walletId: UUID, idempotency_key: str, data: CreditRequest, db_session: AsyncSession):
        try:
            async with db_session.begin():
                # Step 1: Check idempotency FIRST (before locking -- it's just a read)
                request_hash = compute_request_hash(data)
                cached_response = await check_idempotency(idempotency_key=idempotency_key, request_hash=request_hash, db_session=db_session)
                if cached_response:
                    return cached_response
                #  Step 2: Lock the wallet row
                get_wallet_result = await db_session.execute(select(WalletAccount).where(WalletAccount.id == walletId).with_for_update())
                wallet = get_wallet_result.scalar_one_or_none()
                if wallet is None:
                    raise WalletNotFoundError()
                if wallet.status is not AccountStatus.ACTIVE:
                    raise WalletFrozenError()

                 # Step 3: You need a SYSTEM account as the source
                 #  (the money comes from somewhere)
                 #  For now, you can query it or hardcode a known system account ID

                get_system_account_result = await db_session.execute(select(WalletAccount).where(WalletAccount.account_type == AccountType.SYSTEM))
                system_account = get_system_account_result.scalar_one_or_none()
                if system_account is None:
                    raise WalletNotFoundError()

                # db_session.add(IdempotencyKey())
                # Step 4: Create the Transaction
                transaction = Transaction(
                    source_account_id=system_account.id,
                    destination_account_id=wallet.id,
                    transaction_type=TransactionType.CREDIT,
                    idempotency_key=idempotency_key,
                    amount=data.amount,
                    status=TransactionStatus.PENDING,
                )
                db_session.add(transaction)
                await db_session.flush()
                # Step 5: Create 2 LedgerEntries (double-entry)
                # DEBIT from system (money leaves system)
                debit_ledger_entry = LedgerEntry(
                    account_id=system_account.id,
                    amount=data.amount,
                    transaction_id=transaction.id,
                    running_balance=system_account.cached_balance - data.amount,
                    entry_type=EntryType.DEBIT,
                )
                # CREDIT to user wallet (money enters wallet)
                credit_ledger_entry = LedgerEntry(
                    account_id=wallet.id,
                    amount=data.amount,
                    transaction_id=transaction.id,
                    running_balance=wallet.cached_balance + data.amount,
                    entry_type=EntryType.CREDIT,
                )

                db_session.add_all([debit_ledger_entry, credit_ledger_entry])

                # credit the wallet
                wallet.cached_balance += data.amount
                system_account.cached_balance -= data.amount

                response = {
                    "transaction_id": str(transaction.id),
                    "amount": data.amount,
                    "status": TransactionStatus.COMPLETED,
                }
                # create a new row for the idempotency key
                # db_session.add(IdempotencyKey(
                #     key=idempotency_key,
                #     request_hash="...",  # hash of the request
                #     request_json=response,
                # ))
                await save_idempotency(idempotency_key=idempotency_key, request_hash=request_hash, request_data=data, db_session=db_session)
            return response
        except Exception as e:
            logging.error(f"Failed to credit wallet: {e}", exc_info=True)
            raise WalletError(f"Failed to credit wallet")

    async def debit_wallet(self, wallet_id: UUID, idempotency_key: str, data: DebitRequest, db_session: AsyncSession):
        try:
            async with db_session.begin():
                # check idempotency
                get_idempotency_result = await db_session.execute(select(IdempotencyKey).where(IdempotencyKey.key == idempotency_key))
                result = get_idempotency_result.scalar_one_or_none()
                if result:
                    return result.request_json
                # lock the wallet
                get_wallet_result = await db_session.execute(select(WalletAccount).where(WalletAccount.id == wallet_id).with_for_update())
                wallet = get_wallet_result.scalar_one_or_none()
                if wallet is None:
                    raise WalletNotFoundError()
                if wallet.status is not AccountStatus.ACTIVE:
                    raise WalletFrozenError()
                if wallet.cached_balance < data.amount:
                    raise InsufficientBalanceError()

                get_system_account_result = await db_session.execute(select(WalletAccount).where(WalletAccount.account_type == AccountType.SYSTEM))
                system_account = get_system_account_result.scalar_one_or_none()
                if system_account is None:
                    raise WalletError("System account not found")

                # create the transaction
                transaction = Transaction(
                    source_account_id=wallet.id,
                    destination_account_id=system_account.id,
                    amount=data.amount,
                    idempotency_key=idempotency_key,
                    transaction_type=TransactionType.DEBIT,
                    status=TransactionStatus.COMPLETED
                )
                db_session.add(transaction)
                await db_session.flush()

                debit_leger_entry = LedgerEntry(
                    account_id=wallet.id,
                    transaction_id=transaction.id,
                    amount=data.amount,
                    running_balance=wallet.cached_balance-data.amount,
                    entry_type=EntryType.DEBIT
                )
                credit_leger_entry = LedgerEntry(
                    account_id=system_account.id,
                    transaction_id=transaction.id,
                    amount=data.amount,
                    running_balance=system_account.cached_balance+data.amount,
                    entry_type=EntryType.CREDIT
                )

                db_session.add_all([debit_leger_entry, credit_leger_entry])

                wallet.cached_balance -= data.amount
                system_account.cached_balance += data.amount

                response = {
                    "transaction_id": str(transaction.id),
                    "amount": data.amount,
                    "status": TransactionStatus.COMPLETED,
                }

                # create idemoptency record
                db_session.add(IdempotencyKey(
                    key=idempotency_key,
                    request_hash="...",  # hash of the request
                    request_json=response,
                ))

            return response

        except Exception as e:
            logging.error(f"failed to debit wallet: {e}", exc_info=True)
            if isinstance(e, WalletError):
                raise e
            raise WalletError("failed to debit wallet")

    async def transfer_wallet(self, idempotency_key: str, data: TransferRequest, db_session: AsyncSession):
        try:
            async with db_session.begin():
                # check for idempotency
                request_hash = compute_request_hash(data)
                cached_response = await check_idempotency(idempotency_key=idempotency_key, request_hash=request_hash, db_session=db_session)
                if cached_response:
                    return cached_response
                # check wallet(both source and destination) is valid
                get_source_wallet_account_result = await db_session.execute(select(WalletAccount).where(WalletAccount.id == data.source_account_id))
                source_wallet_acoount = get_source_wallet_account_result.scalar_one_or_none()
                if source_wallet_acoount is None:
                    raise WalletNotFoundError()
                if source_wallet_acoount.status != AccountStatus.ACTIVE:
                    raise WalletFrozenError()
                if source_wallet_acoount.cached_balance < data.amount:
                    raise InsufficientBalanceError()
                get_destination_wallet_account_result = await db_session.execute(select(WalletAccount).where(WalletAccount.id == data.destination_account_id))
                dest_wallet_acoount = get_destination_wallet_account_result.scalar_one_or_none()
                if dest_wallet_acoount is None:
                    raise WalletNotFoundError()
                if dest_wallet_acoount.status != AccountStatus.ACTIVE:
                    raise WalletFrozenError()
                # lock both accounts(make sure you lock in order. if not locked in order you can create deadlock)
                # Request A: Transfer from Wallet_1 → Wallet_2
                #  Lock source (Wallet_1) first, then destination (Wallet_2)
                # Request B: Transfer from Wallet_2 → Wallet_1
                #   Lock source (Wallet_2) first, then destination (Wallet_1)
                # in the above case if you lock in reverse order you can create deadlock.
                # so you need to lock in order.
                # like this:
                #   Request A: Transfer from Wallet_1 → Wallet_2
                #   min(1,2) = Wallet_1, max(1,2) = Wallet_2
                #   Lock: Wallet_1, then Wallet_2

                # Request B: Transfer from Wallet_2 → Wallet_1
                #   min(2,1) = Wallet_1, max(2,1) = Wallet_2
                #   Lock: Wallet_1, then Wallet_2

                # lock the accounts in order
                min_wallet_id = min(source_wallet_acoount.id,
                                    dest_wallet_acoount.id)
                max_wallet_id = max(source_wallet_acoount.id,
                                    dest_wallet_acoount.id)
                await db_session.execute(select(WalletAccount).where(WalletAccount.id == min_wallet_id).with_for_update())
                await db_session.execute(select(WalletAccount).where(WalletAccount.id == max_wallet_id).with_for_update())
                # create the transaction
                transaction = Transaction(
                    source_account_id=source_wallet_acoount.id,
                    destination_account_id=dest_wallet_acoount.id,
                    amount=data.amount,
                    idempotency_key=idempotency_key,
                    transaction_type=TransactionType.TRANSFER,
                    status=TransactionStatus.COMPLETED,
                )
                db_session.add(transaction)
                await db_session.flush()
                # create the ledger entries
                debit_ledger_entry = LedgerEntry(
                    account_id=source_wallet_acoount.id,
                    transaction_id=transaction.id,
                    amount=data.amount,
                    running_balance=source_wallet_acoount.cached_balance-data.amount,
                    entry_type=EntryType.DEBIT,
                )
                credit_ledger_entry = LedgerEntry(
                    account_id=dest_wallet_acoount.id,
                    transaction_id=transaction.id,
                    amount=data.amount,
                    running_balance=dest_wallet_acoount.cached_balance+data.amount,
                    entry_type=EntryType.CREDIT,
                )
                db_session.add_all([debit_ledger_entry, credit_ledger_entry])
                # update the balances
                source_wallet_acoount.cached_balance -= data.amount
                dest_wallet_acoount.cached_balance += data.amount

                response = {
                    "transaction_id": str(transaction.id),
                    "amount": data.amount,
                    "status": TransactionStatus.COMPLETED,
                }
                # create the idempotency key
                await save_idempotency(idempotency_key=idempotency_key, request_hash=request_hash, request_data=data, db_session=db_session)
            return response

        except Exception as e:
            logging.error(f"failed to transfer wallet {e}", exc_info=True)
            if isinstance(e, WalletError):
                raise e
            raise WalletError("failed to transfer wallet")


wallet_crud_service = WalletCrudService()
