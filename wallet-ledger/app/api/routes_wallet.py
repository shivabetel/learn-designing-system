from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.core import get_db_session
from app.schemas.wallet import CreateWalletRequest
from app.schemas.transaction import CreditRequest, DebitRequest, TransferRequest
from app.crud.wallet_service import wallet_crud_service
from app.schemas.wallet import WalletResponse, BalanceResponse
router = APIRouter(prefix="/wallets")


@router.post("/", response_model=WalletResponse)
async def create_wallet(request: CreateWalletRequest, db_session: AsyncSession = Depends(get_db_session)):
    # return {"message": "Wallet created successfully"}
    wallet = await wallet_crud_service.create_wallet(db_session=db_session, data=request)
    return wallet


@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(wallet_id: str, db_session: AsyncSession = Depends(get_db_session)):
    wallet = await wallet_crud_service.get_wallet(walletId=wallet_id, db_session=db_session)
    return wallet


@router.get("/{wallet_id}/balance", response_model=BalanceResponse)
async def get_wallet_balance(wallet_id: str, db_session: AsyncSession = Depends(get_db_session)):
    balance = await wallet_crud_service.get_balance(walletId=wallet_id, db_session=db_session)
    return BalanceResponse(account_id=wallet_id, balance=balance)


@router.post("/{wallet_id}/credit")
async def credit_wallet(wallet_id: str,
                        request: CreditRequest,
                        idempotency_key: str = Header(...,
                                                      alias="Idempotency-Key"),
                        db_session: AsyncSession = Depends(get_db_session)):
    response = await wallet_crud_service.credit_wallet(walletId=wallet_id, data=request, db_session=db_session, idempotency_key=idempotency_key)
    return response


@router.post("/{wallet_id}/debit")
async def debit_wallet(wallet_id: str, request: DebitRequest, idempotency_key: str = Header(..., alias="Idempotency-Key"), db_session: AsyncSession = Depends(get_db_session)):
    response = await wallet_crud_service.debit_wallet(wallet_id=wallet_id, data=request, db_session=db_session, idempotency_key=idempotency_key)
    return response


@router.post("/transfer")
async def transfer_wallet(request: TransferRequest, idempotency_key: str = Header(..., alias="Idemopotency-Key"), db_session: AsyncSession = Depends(get_db_session)):
    response = await wallet_crud_service.transfer_wallet(idempotency_key=idempotency_key, data=request, db_session=db_session)
    return response
