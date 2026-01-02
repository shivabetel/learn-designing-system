from fastapi import APIRouter, Depends, HTTPException
from app.crud.screen import ScreenCreationError, crud_screen
from app.db.session import getDB_session
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.screen import ScreenCreate, ScreenResponse
router = APIRouter(
    prefix='/screen'
)


@router.get("/{screen_id}", response_model=ScreenResponse)
async def get_screen(screen_id: int, db: AsyncSession = Depends(getDB_session)):
    result = await crud_screen.get_screen(db, screen_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Screen not found")
    return result


@router.post("/theatre/{theatre_id}", response_model=ScreenResponse)
async def create_screen_by_theatre_id(theatre_id: int, screen: ScreenCreate, db: AsyncSession = Depends(getDB_session)):
    try:
        return await crud_screen.create_screen_by_theatre_id(db, theatre_id, screen)
    except ScreenCreationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[ScreenResponse])
async def get_all_screens(db: AsyncSession = Depends(getDB_session)):
    return await crud_screen.get_all_screens(db)


@router.get("/theatre/{theatre_id}", response_model=list[ScreenResponse])
async def getScreenByTheatreId(theatre_id: int, db: AsyncSession = Depends(getDB_session)):
    return await crud_screen.getScreenByTheatreId(db, theatre_id)
