"""Live price endpoints"""

from fastapi import APIRouter, Depends

from app.auth.security import get_current_user
from app.services.price_service import price_service

router = APIRouter()


@router.get("/prices")
async def get_prices(current_user=Depends(get_current_user)):
    return {"prices": price_service.get_prices()}