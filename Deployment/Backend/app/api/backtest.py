"""Strategy performance and backtest endpoints"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.backtest_service import backtest_service

router = APIRouter()


@router.get("/backtest/summary")
async def get_performance_summary(
    pair: Optional[str] = Query(None, description="Filter by pair (e.g., 'EURUSD')")
):
    """
    Get overall strategy performance metrics.
    
    Args:
        pair: Optional pair filter
    
    Returns:
        Performance summary with win rate, pips, profit factor, etc.
    """
    result = backtest_service.get_performance_summary(pair)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/backtest/equity")
async def get_equity_curve(
    pair: Optional[str] = Query(None, description="Filter by pair (e.g., 'EURUSD')")
):
    """
    Get cumulative pips over time (equity curve).
    
    Args:
        pair: Optional pair filter
    
    Returns:
        Time series of cumulative pips
    """
    result = backtest_service.get_equity_curve(pair)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/backtest/drawdown")
async def get_drawdown_curve(
    pair: Optional[str] = Query(None, description="Filter by pair (e.g., 'EURUSD')")
):
    """
    Get drawdown analysis over time.
    
    Args:
        pair: Optional pair filter
    
    Returns:
        Time series of drawdown in pips and percentage
    """
    result = backtest_service.get_drawdown_curve(pair)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/backtest/pairs")
async def get_pair_comparison():
    """
    Compare performance across all currency pairs.
    
    Returns:
        Performance metrics for each pair
    """
    result = backtest_service.get_pair_comparison()
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/backtest/trades")
async def get_recent_trades(
    limit: int = Query(20, ge=1, le=100, description="Number of signals to return"),
    pair: Optional[str] = Query(None, description="Filter by pair (e.g., 'EURUSD')")
):
    """
    Get recent signals with simulated outcomes.
    
    Args:
        limit: Number of signals to return (1-100)
        pair: Optional pair filter
    
    Returns:
        List of recent signals with entry, exit, pips, etc.
    """
    result = backtest_service.get_recent_signals(limit, pair)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result
