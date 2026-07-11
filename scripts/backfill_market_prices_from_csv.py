from __future__ import annotations
import _bootstrap  # noqa: F401

import argparse
import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.db.database import SessionLocal
from app.services.market_price_service import upsert_market_price


REQUIRED_COLUMNS = {
    "symbol",
    "price_date",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
}


OPTIONAL_COLUMNS = {
    "adjusted_close_price",
    "volume",
    "currency",
    "exchange",
    "instrument_type",
    "interval",
    "source",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill historical market prices from a CSV file."
    )

    parser.add_argument(
        "--file",
        required=True,
        help="Path to CSV file containing historical OHLCV market prices.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    csv_path = Path(args.file)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    rows = load_csv_rows(csv_path)

    db = SessionLocal()

    processed_count = 0
    failed_count = 0
    failed_rows: list[dict[str, Any]] = []

    try:
        for row_number, row in enumerate(rows, start=2):
            try:
                upsert_market_price(
                    db,
                    symbol=row["symbol"],
                    price_date=parse_price_date(row["price_date"]),
                    open_price=empty_to_none(row.get("open_price")),
                    high_price=empty_to_none(row.get("high_price")),
                    low_price=empty_to_none(row.get("low_price")),
                    close_price=empty_to_none(row.get("close_price")),
                    adjusted_close_price=empty_to_none(
                        row.get("adjusted_close_price")
                    ),
                    volume=empty_to_none(row.get("volume")),
                    currency=empty_to_none(row.get("currency")),
                    exchange=empty_to_none(row.get("exchange")),
                    instrument_type=empty_to_none(row.get("instrument_type")),
                    interval=empty_to_default(row.get("interval"), "1d"),
                    source=empty_to_default(row.get("source"), "manual_csv"),
                )

                processed_count += 1

            except Exception as exc:
                failed_count += 1
                failed_rows.append(
                    {
                        "row_number": row_number,
                        "symbol": row.get("symbol"),
                        "price_date": row.get("price_date"),
                        "error": str(exc),
                    }
                )

        print("")
        print("Market price CSV backfill complete.")
        print(f"CSV file: {csv_path}")
        print(f"Rows processed successfully: {processed_count}")
        print(f"Rows failed: {failed_count}")

        if failed_rows:
            print("")
            print("Failed rows:")
            for failed_row in failed_rows:
                print(
                    "row_number={row_number}, symbol={symbol}, "
                    "price_date={price_date}, error={error}".format(
                        row_number=failed_row["row_number"],
                        symbol=failed_row["symbol"],
                        price_date=failed_row["price_date"],
                        error=failed_row["error"],
                    )
                )

    finally:
        db.close()


def load_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)

        if reader.fieldnames is None:
            raise ValueError("CSV file does not contain a header row")

        normalized_headers = {
            header.strip() for header in reader.fieldnames if header
        }

        missing_columns = REQUIRED_COLUMNS - normalized_headers

        if missing_columns:
            raise ValueError(
                "CSV file is missing required columns: "
                + ", ".join(sorted(missing_columns))
            )

        allowed_columns = REQUIRED_COLUMNS | OPTIONAL_COLUMNS
        unexpected_columns = normalized_headers - allowed_columns

        if unexpected_columns:
            raise ValueError(
                "CSV file contains unexpected columns: "
                + ", ".join(sorted(unexpected_columns))
            )

        rows: list[dict[str, str]] = []

        for row in reader:
            normalized_row = {
                key.strip(): value.strip() if value is not None else ""
                for key, value in row.items()
                if key is not None
            }

            rows.append(normalized_row)

        return rows


def parse_price_date(value: str) -> date:
    if not value or not value.strip():
        raise ValueError("price_date is required")

    return datetime.strptime(value.strip(), "%Y-%m-%d").date()


def empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()

    if not normalized_value:
        return None

    return normalized_value


def empty_to_default(value: str | None, default_value: str) -> str:
    if value is None:
        return default_value

    normalized_value = value.strip()

    if not normalized_value:
        return default_value

    return normalized_value


if __name__ == "__main__":
    main()