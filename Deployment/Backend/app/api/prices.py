"""Live price endpoints"""

from fastapi import APIRouter

from app.services.price_service import price_service

router = APIRouter()


@router.get("/prices")
async def get_prices():
    """Get live prices for all pairs"""
    return {"prices": price_service.get_prices()}
