"""Strategy performance and backtest endpoints"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.backtest_service import backtest_service

router = APIRouter()


@router.get("/backtest/summary")
async def get_performance_summary(
    pair: Optional[str] = Query(None, description="Filter by pair (e.g., 'EURUSD')")
):
    result = backtest_service.get_performance_summary(pair)
    if "error" in result:
        # Return empty state instead of 404 — no data yet is not an error
        return {
            "total_signals": 0, "winning_signals": 0, "losing_signals": 0,
            "win_rate": 0.0, "total_pips": 0.0, "avg_win_pips": 0.0,
            "avg_loss_pips": 0.0, "profit_factor": 0.0, "max_drawdown_pips": 0.0,
            "max_drawdown_pct": 0.0, "sharpe_ratio": 0.0,
            "best_signal_pips": 0.0, "worst_signal_pips": 0.0,
            "avg_signal_duration_hours": 0.0, "status": "no_data",
        }
    return result


@router.get("/backtest/equity")
async def get_equity_curve(
    pair: Optional[str] = Query(None, description="Filter by pair (e.g., 'EURUSD')")
):
    result = backtest_service.get_equity_curve(pair)
    if "error" in result:
        return {"type": "equity_curve", "data": [], "pair_filter": pair}
    return result


@router.get("/backtest/drawdown")
async def get_drawdown_curve(
    pair: Optional[str] = Query(None, description="Filter by pair (e.g., 'EURUSD')")
):
    result = backtest_service.get_drawdown_curve(pair)
    if "error" in result:
        return {"type": "drawdown_curve", "data": [], "pair_filter": pair}
    return result


@router.get("/backtest/pairs")
async def get_pair_comparison():
    result = backtest_service.get_pair_comparison()
    if "error" in result:
        return {"type": "pair_comparison", "pairs": []}
    return result


@router.get("/backtest/trades")
async def get_recent_trades(
    limit: int = Query(20, ge=1, le=100),
    pair: Optional[str] = Query(None)
):
    result = backtest_service.get_recent_signals(limit, pair)
    if "error" in result:
        return {"type": "recent_signals", "signals": []}
    return result
