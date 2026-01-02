from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, APIRouter, HTTPException
from app.crud.theatre import crud_theatre
from app.db.session import getDB_session
from app.schemas.theatre import TheatreCreate, TheatreResponse, TheatreUpdate


router = APIRouter(prefix="/theatre")


@router.get("/{theatre_id}", response_model=TheatreResponse)
async def get_theatre(
        theatre_id: int,
        db: AsyncSession = Depends(getDB_session)):
    result = await crud_theatre.get_theatre(db, theatre_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Theatre not found")
    return result


@router.post("/", response_model=TheatreResponse)
async def create_theatre(
        theatre: TheatreCreate,
        db: AsyncSession = Depends(getDB_session)):
    return await crud_theatre.create_theatre(db, theatre)


@router.get("/", response_model=list[TheatreResponse])
async def get_all_theatres(
        db: AsyncSession = Depends(getDB_session)):
    return await crud_theatre.get_all_theatres(db)


@router.put("/{theatre_id}", response_model=TheatreResponse)
async def update_theatre(
        theatre_id: int,
        theatre: TheatreUpdate,
        db: AsyncSession = Depends(getDB_session)):
    result = await crud_theatre.update_theatre(db=db, theatre_id=theatre_id, data=theatre)
    if result is None:
        raise HTTPException(status_code=404, detail="Theatre not found")

    return result
