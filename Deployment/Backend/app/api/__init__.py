"""API routes"""

from app.api import health, signals, websocket, prices, calendar, news, alphabot

__all__ = ["health", "signals", "websocket", "prices", "calendar", "news", "alphabot"]