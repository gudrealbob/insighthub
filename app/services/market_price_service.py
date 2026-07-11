from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models.market_price import MarketPrice


def normalize_symbol(symbol: str) -> str:
    """
    Normalize market symbols before persistence.

    Current rule:
    - Strip leading/trailing whitespace
    - Convert to uppercase

    Future enrichment such as exchange suffixes or symbol mapping belongs
    in TD-001 / TD-002, not here.
    """
    if not symbol:
        raise ValueError("symbol is required")

    normalized_symbol = symbol.strip().upper()

    if not normalized_symbol:
        raise ValueError("symbol is required")

    return normalized_symbol


def upsert_market_price(
    db: Session,
    *,
    symbol: str,
    price_date: date,
    open_price: Decimal | float | int | str | None = None,
    high_price: Decimal | float | int | str | None = None,
    low_price: Decimal | float | int | str | None = None,
    close_price: Decimal | float | int | str | None = None,
    adjusted_close_price: Decimal | float | int | str | None = None,
    volume: Decimal | float | int | str | None = None,
    interval: str = "1d",
    source: str = "manual",
    currency: str | None = None,
    exchange: str | None = None,
    instrument_type: str | None = None,
) -> MarketPrice:
    """
    Insert or update one market price row.

    Uniqueness is based on:
    - symbol
    - price_date
    - interval
    - source

    This makes the operation safe for repeated ingestion/backfill runs.
    """

    normalized_symbol = normalize_symbol(symbol)

    if not price_date:
        raise ValueError("price_date is required")

    normalized_interval = interval.strip().lower() if interval else "1d"
    normalized_source = source.strip().lower() if source else "manual"

    existing_price = (
        db.query(MarketPrice)
        .filter(MarketPrice.symbol == normalized_symbol)
        .filter(MarketPrice.price_date == price_date)
        .filter(MarketPrice.interval == normalized_interval)
        .filter(MarketPrice.source == normalized_source)
        .one_or_none()
    )

    if existing_price:
        existing_price.open_price = _to_decimal_or_none(open_price)
        existing_price.high_price = _to_decimal_or_none(high_price)
        existing_price.low_price = _to_decimal_or_none(low_price)
        existing_price.close_price = _to_decimal_or_none(close_price)
        existing_price.adjusted_close_price = _to_decimal_or_none(
            adjusted_close_price
        )
        existing_price.volume = _to_decimal_or_none(volume)
        existing_price.currency = _normalize_optional_upper(currency)
        existing_price.exchange = _normalize_optional_upper(exchange)
        existing_price.instrument_type = _normalize_optional_lower(
            instrument_type
        )

        db.add(existing_price)
        db.commit()
        db.refresh(existing_price)

        return existing_price

    market_price = MarketPrice(
        symbol=normalized_symbol,
        price_date=price_date,
        interval=normalized_interval,
        source=normalized_source,
        open_price=_to_decimal_or_none(open_price),
        high_price=_to_decimal_or_none(high_price),
        low_price=_to_decimal_or_none(low_price),
        close_price=_to_decimal_or_none(close_price),
        adjusted_close_price=_to_decimal_or_none(adjusted_close_price),
        volume=_to_decimal_or_none(volume),
        currency=_normalize_optional_upper(currency),
        exchange=_normalize_optional_upper(exchange),
        instrument_type=_normalize_optional_lower(instrument_type),
    )

    db.add(market_price)
    db.commit()
    db.refresh(market_price)

    return market_price


def upsert_market_prices(
    db: Session,
    market_price_rows: Iterable[dict[str, Any]],
) -> list[MarketPrice]:
    """
    Insert or update multiple market price rows.

    Each row must provide at minimum:
    - symbol
    - price_date

    The function commits per row through upsert_market_price.
    This is intentionally simple and reliable for Sprint 4.
    Bulk optimization can be added later as technical debt if needed.
    """

    saved_prices: list[MarketPrice] = []

    for row in market_price_rows:
        saved_price = upsert_market_price(
            db,
            symbol=row["symbol"],
            price_date=row["price_date"],
            open_price=row.get("open_price"),
            high_price=row.get("high_price"),
            low_price=row.get("low_price"),
            close_price=row.get("close_price"),
            adjusted_close_price=row.get("adjusted_close_price"),
            volume=row.get("volume"),
            interval=row.get("interval", "1d"),
            source=row.get("source", "manual"),
            currency=row.get("currency"),
            exchange=row.get("exchange"),
            instrument_type=row.get("instrument_type"),
        )

        saved_prices.append(saved_price)

    return saved_prices


def _to_decimal_or_none(
    value: Decimal | float | int | str | None,
) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    value_as_text = str(value).strip()

    if value_as_text == "":
        return None

    return Decimal(value_as_text)


def _normalize_optional_upper(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip().upper()

    if not normalized_value:
        return None

    return normalized_value


def _normalize_optional_lower(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip().lower()

    if not normalized_value:
        return None

    return normalized_value