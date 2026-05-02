from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OpenTradeRequest(BaseModel):
    symbol: str
    side: str
    entry_price: float
    quantity: float

    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    source_signal_id: Optional[str] = None


class CloseTradeRequest(BaseModel):
    exit_price: float


class TradeResponse(BaseModel):
    id: int

    symbol: str
    side: str

    entry_price: float
    exit_price: Optional[float]

    stop_loss: Optional[float]
    take_profit: Optional[float]

    quantity: float

    status: str

    pnl: float

    opened_at: datetime
    closed_at: Optional[datetime]

    source_signal_id: Optional[str]

    class Config:
        from_attributes = True


class PortfolioResponse(BaseModel):
    balance: float
    initial_balance: float
    realized_pnl: float