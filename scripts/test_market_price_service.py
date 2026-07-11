from __future__ import annotations

import _bootstrap  # noqa: F401

from datetime import date
from decimal import Decimal

from app.db.database import SessionLocal
from app.services.market_price_service import upsert_market_price


def main() -> None:
    db = SessionLocal()

    try:
        saved_price = upsert_market_price(
            db,
            symbol=" aapl ",
            price_date=date(2026, 7, 8),
            interval="1d",
            source="manual",
            open_price=Decimal("210.00"),
            high_price=Decimal("215.50"),
            low_price=Decimal("208.75"),
            close_price=Decimal("214.20"),
            adjusted_close_price=Decimal("214.20"),
            volume=Decimal("75000000"),
            currency="usd",
            exchange="nasdaq",
            instrument_type="stock",
        )

        print("Saved market price:")
        print(f"id={saved_price.id}")
        print(f"symbol={saved_price.symbol}")
        print(f"price_date={saved_price.price_date}")
        print(f"interval={saved_price.interval}")
        print(f"source={saved_price.source}")
        print(f"open_price={saved_price.open_price}")
        print(f"high_price={saved_price.high_price}")
        print(f"low_price={saved_price.low_price}")
        print(f"close_price={saved_price.close_price}")
        print(f"adjusted_close_price={saved_price.adjusted_close_price}")
        print(f"volume={saved_price.volume}")
        print(f"currency={saved_price.currency}")
        print(f"exchange={saved_price.exchange}")
        print(f"instrument_type={saved_price.instrument_type}")

        updated_price = upsert_market_price(
            db,
            symbol="AAPL",
            price_date=date(2026, 7, 8),
            interval="1d",
            source="manual",
            open_price=Decimal("211.00"),
            high_price=Decimal("216.00"),
            low_price=Decimal("209.00"),
            close_price=Decimal("215.00"),
            adjusted_close_price=Decimal("215.00"),
            volume=Decimal("76000000"),
            currency="USD",
            exchange="NASDAQ",
            instrument_type="stock",
        )

        print("")
        print("Updated same market price:")
        print(f"id={updated_price.id}")
        print(f"symbol={updated_price.symbol}")
        print(f"price_date={updated_price.price_date}")
        print(f"interval={updated_price.interval}")
        print(f"source={updated_price.source}")
        print(f"open_price={updated_price.open_price}")
        print(f"high_price={updated_price.high_price}")
        print(f"low_price={updated_price.low_price}")
        print(f"close_price={updated_price.close_price}")
        print(f"adjusted_close_price={updated_price.adjusted_close_price}")
        print(f"volume={updated_price.volume}")
        print(f"currency={updated_price.currency}")
        print(f"exchange={updated_price.exchange}")
        print(f"instrument_type={updated_price.instrument_type}")

    finally:
        db.close()


if __name__ == "__main__":
    main()