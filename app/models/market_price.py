from __future__ import annotations

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)

from app.models.base import Base


class MarketPrice(Base):
    """
    Historical OHLCV market price data.

    This table stores normalized market prices used later for
    recommendation performance tracking.

    It is intentionally separate from recommendations because prices
    are reusable market facts, not recommendation-specific data.
    """

    __tablename__ = "market_prices"

    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "price_date",
            "interval",
            "source",
            name="uq_market_price_symbol_date_interval_source",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    symbol = Column(
        String(30),
        nullable=False,
        index=True,
    )

    price_date = Column(
        Date,
        nullable=False,
        index=True,
    )

    interval = Column(
        String(20),
        nullable=False,
        default="1d",
        server_default="1d",
    )

    source = Column(
        String(50),
        nullable=False,
        default="manual",
        server_default="manual",
    )

    open_price = Column(
        Numeric(18, 6),
        nullable=True,
    )

    high_price = Column(
        Numeric(18, 6),
        nullable=True,
    )

    low_price = Column(
        Numeric(18, 6),
        nullable=True,
    )

    close_price = Column(
        Numeric(18, 6),
        nullable=True,
    )

    adjusted_close_price = Column(
        Numeric(18, 6),
        nullable=True,
    )

    volume = Column(
        Numeric(24, 4),
        nullable=True,
    )

    currency = Column(
        String(10),
        nullable=True,
    )

    exchange = Column(
        String(30),
        nullable=True,
    )

    instrument_type = Column(
        String(30),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )