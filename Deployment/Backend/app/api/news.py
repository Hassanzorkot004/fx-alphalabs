"""News endpoints"""

from fastapi import APIRouter

from app.services.news_service import news_service

router = APIRouter()


@router.get("/news")
async def get_news(limit: int = 20):
    """Get recent forex news articles"""
    return {"articles": news_service.get_articles(limit=limit)}
