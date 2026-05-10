"""Economic calendar endpoints"""

from fastapi import APIRouter

from app.services.calendar_service import calendar_service
from app.services.demo_service import is_demo, demo_mode, get_demo_calendar

router = APIRouter()


@router.get("/calendar")
async def get_calendar():
    if is_demo():
        return {"events": get_demo_calendar(demo_mode())}
    return {"events": calendar_service.get_events()}


@router.get("/calendar/upcoming")
async def get_upcoming_events(hours: int = 24):
    if is_demo():
        return {"events": get_demo_calendar(demo_mode())}
    return {"events": calendar_service.get_upcoming(hours)}
