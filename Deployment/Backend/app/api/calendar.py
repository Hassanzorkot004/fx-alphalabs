"""Economic calendar endpoints"""

from fastapi import APIRouter, Depends

from app.auth.security import get_current_user
from app.services.calendar_service import calendar_service

router = APIRouter()


@router.get("/calendar")
async def get_calendar(current_user=Depends(get_current_user)):
    return {"events": calendar_service.get_events()}


@router.get("/calendar/upcoming")
async def get_upcoming_events(
    hours: int = 24,
    current_user=Depends(get_current_user),
):
    return {"events": calendar_service.get_upcoming(hours)}