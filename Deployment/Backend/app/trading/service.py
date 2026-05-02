from datetime import datetime

from sqlalchemy.orm import Session

from app.trading.models import VirtualPortfolio, VirtualTrade


DEFAULT_BALANCE = 10000.0


def get_or_create_portfolio(db: Session, user_id: int):
    portfolio = (
        db.query(VirtualPortfolio)
        .filter(VirtualPortfolio.user_id == user_id)
        .first()
    )

    if portfolio:
        return portfolio

    portfolio = VirtualPortfolio(
        user_id=user_id,
        balance=DEFAULT_BALANCE,
        initial_balance=DEFAULT_BALANCE,
        realized_pnl=0.0,
    )

    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)

    return portfolio


def open_trade(
    db: Session,
    user_id: int,
    symbol: str,
    side: str,
    entry_price: float,
    quantity: float,
    stop_loss: float | None = None,
    take_profit: float | None = None,
    source_signal_id: str | None = None,
):
    trade = VirtualTrade(
        user_id=user_id,
        symbol=symbol,
        side=side,
        entry_price=entry_price,
        quantity=quantity,
        stop_loss=stop_loss,
        take_profit=take_profit,
        source_signal_id=source_signal_id,
        status="OPEN",
    )

    db.add(trade)
    db.commit()
    db.refresh(trade)

    return trade


def close_trade(
    db: Session,
    trade: VirtualTrade,
    exit_price: float,
):
    trade.exit_price = exit_price

    if trade.side == "BUY":
        pnl = (exit_price - trade.entry_price) * trade.quantity
    else:
        pnl = (trade.entry_price - exit_price) * trade.quantity

    trade.pnl = round(pnl, 2)
    trade.status = "CLOSED"
    trade.closed_at = datetime.utcnow()

    portfolio = (
        db.query(VirtualPortfolio)
        .filter(VirtualPortfolio.user_id == trade.user_id)
        .first()
    )

    portfolio.balance += trade.pnl
    portfolio.realized_pnl += trade.pnl

    db.commit()
    db.refresh(trade)

    return trade