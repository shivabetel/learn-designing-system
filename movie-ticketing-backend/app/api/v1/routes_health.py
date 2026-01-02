from fastapi import APIRouter


router = APIRouter();

@router.get("/health", summary="Basic health check endpoint", description="In real systems, this might check DB/Redis connectivity.")
async def health_check():
    """
    Basic health check endpoint.
    In real systems, this might check DB/Redis connectivity.
    """
    return {"status": "ok"}