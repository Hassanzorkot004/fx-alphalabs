from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.database import get_db
from app.auth.security import get_current_user

from app.trading.models import VirtualTrade
from app.trading.schemas import OpenTradeRequest, CloseTradeRequest
from app.trading.service import (
    get_or_create_portfolio,
    open_trade,
    close_trade,
)

router = APIRouter()


def get_user_id(current_user):
    if isinstance(current_user, dict):
        return current_user.get("id")

    return current_user.id


@router.get("/portfolio")
def get_portfolio(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = get_user_id(current_user)
    portfolio = get_or_create_portfolio(db, user_id)

    return {
        "balance": portfolio.balance,
        "initial_balance": portfolio.initial_balance,
        "realized_pnl": portfolio.realized_pnl,
    }


@router.get("/trades")
def get_trades(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = get_user_id(current_user)

    return (
        db.query(VirtualTrade)
        .filter(VirtualTrade.user_id == user_id)
        .order_by(VirtualTrade.opened_at.desc())
        .all()
    )


@router.get("/trades/open")
def get_open_trades(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = get_user_id(current_user)

    return (
        db.query(VirtualTrade)
        .filter(
            VirtualTrade.user_id == user_id,
            VirtualTrade.status == "OPEN",
        )
        .all()
    )


@router.get("/trades/closed")
def get_closed_trades(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = get_user_id(current_user)

    return (
        db.query(VirtualTrade)
        .filter(
            VirtualTrade.user_id == user_id,
            VirtualTrade.status == "CLOSED",
        )
        .all()
    )


@router.post("/open")
def open_virtual_trade(
    payload: OpenTradeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = get_user_id(current_user)

    get_or_create_portfolio(db, user_id)

    trade = open_trade(
        db=db,
        user_id=user_id,
        symbol=payload.symbol,
        side=payload.side,
        entry_price=payload.entry_price,
        quantity=payload.quantity,
        stop_loss=payload.stop_loss,
        take_profit=payload.take_profit,
        source_signal_id=payload.source_signal_id,
    )

    return trade


@router.post("/close/{trade_id}")
def close_virtual_trade(
    trade_id: int,
    payload: CloseTradeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user_id = get_user_id(current_user)

    trade = (
        db.query(VirtualTrade)
        .filter(
            VirtualTrade.id == trade_id,
            VirtualTrade.user_id == user_id,
        )
        .first()
    )

    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    if trade.status == "CLOSED":
        raise HTTPException(status_code=400, detail="Trade already closed")

    return close_trade(
        db=db,
        trade=trade,
        exit_price=payload.exit_price,
    )