"""Chart data endpoints"""

from fastapi import APIRouter, HTTPException, Query

from app.services.chart_service import chart_service

router = APIRouter()


@router.get("/charts/price/{pair}")
async def get_price_chart(
    pair: str,
    period: str = Query("24h", regex="^(1h|4h|24h|7d)$")
):
    """
    Get OHLC price chart data with signal overlays.
    
    Args:
        pair: Currency pair (e.g., "EURUSD")
        period: Time period - "1h", "4h", "24h", or "7d"
    
    Returns:
        Chart data with candles and signal levels
    """
    result = chart_service.get_price_chart(pair, period)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/charts/indicator/{pair}/{indicator}")
async def get_indicator_chart(
    pair: str,
    indicator: str,
    period: str = Query("24h", regex="^(1h|4h|24h|7d)$")
):
    """
    Get technical indicator chart data.
    
    Args:
        pair: Currency pair (e.g., "EURUSD")
        indicator: Indicator type - "rsi", "macd", or "bb" (Bollinger Bands)
        period: Time period - "1h", "4h", "24h", or "7d"
    
    Returns:
        Indicator data with appropriate levels
    """
    if indicator not in ["rsi", "macd", "bb"]:
        raise HTTPException(status_code=400, detail=f"Unknown indicator: {indicator}")
    
    result = chart_service.get_indicator_chart(pair, indicator, period)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/charts/agents/{pair}")
async def get_agent_confidence_chart(pair: str):
    """
    Get agent confidence breakdown chart.
    
    Args:
        pair: Currency pair (e.g., "EURUSD")
    
    Returns:
        Agent confidence data over time
    """
    result = chart_service.get_agent_confidence_chart(pair)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/charts/risk/{pair}")
async def get_risk_visualization(pair: str):
    """
    Get risk/reward visualization data.
    
    Args:
        pair: Currency pair (e.g., "EURUSD")
    
    Returns:
        Risk metrics and trade levels
    """
    result = chart_service.get_risk_visualization(pair)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result
