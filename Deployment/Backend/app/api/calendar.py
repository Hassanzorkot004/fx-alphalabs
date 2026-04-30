"""Economic calendar endpoints"""

from fastapi import APIRouter

from app.services.calendar_service import calendar_service

router = APIRouter()


@router.get("/calendar")
async def get_calendar():
    """Get all economic events for this week"""
    return {"events": calendar_service.get_events()}


@router.get("/calendar/upcoming")
async def get_upcoming_events(hours: int = 24):
    """Get upcoming events within N hours"""
    return {"events": calendar_service.get_upcoming(hours)}
