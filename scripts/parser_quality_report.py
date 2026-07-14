from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from sqlalchemy import func

from app.db.database import SessionLocal
from app.models.message import Message
from app.models.normalized_message import NormalizedMessage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate parser-quality counts and unresolved-message CSV output."
    )
    parser.add_argument(
        "--output",
        default="output/parser_quality/parser_unresolved.csv",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        rows = (
            db.query(Message, NormalizedMessage)
            .join(NormalizedMessage, NormalizedMessage.message_id == Message.id)
            .order_by(Message.id)
            .all()
        )

        status_counts = Counter(normalized.parser_status for _, normalized in rows)
        print("Parser status counts")
        for status, count in sorted(status_counts.items()):
            print(f"{status}: {count}")

        unresolved_statuses = {
            "UNSUPPORTED_FORMAT",
            "VALIDATION_FAILED",
            "MULTIPLE_RECS",
        }
        unresolved = [
            (message, normalized)
            for message, normalized in rows
            if normalized.parser_status in unresolved_statuses
        ]

        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "message_id",
                    "channel_id",
                    "external_message_id",
                    "message_date",
                    "parser_status",
                    "symbol",
                    "instrument_type",
                    "action",
                    "message_text",
                ],
            )
            writer.writeheader()
            for message, normalized in unresolved:
                writer.writerow(
                    {
                        "message_id": message.id,
                        "channel_id": message.channel_id,
                        "external_message_id": message.external_message_id,
                        "message_date": message.message_date,
                        "parser_status": normalized.parser_status,
                        "symbol": normalized.symbol,
                        "instrument_type": normalized.instrument_type,
                        "action": normalized.action,
                        "message_text": message.message_text,
                    }
                )

        print(f"Unresolved rows: {len(unresolved)}")
        print(f"CSV: {output_path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
