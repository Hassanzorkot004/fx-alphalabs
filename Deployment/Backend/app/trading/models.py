from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey,
)

from app.auth.database import Base


class VirtualPortfolio(Base):
    __tablename__ = "virtual_portfolios"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    balance = Column(Float, default=10000.0)
    initial_balance = Column(Float, default=10000.0)

    realized_pnl = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)


class VirtualTrade(Base):
    __tablename__ = "virtual_trades"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    symbol = Column(String, nullable=False)

    side = Column(String, nullable=False)

    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)

    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)

    quantity = Column(Float, nullable=False)

    status = Column(String, default="OPEN")

    pnl = Column(Float, default=0.0)

    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    source_signal_id = Column(String, nullable=True)