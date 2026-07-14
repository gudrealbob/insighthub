from __future__ import annotations

import argparse
import json

from app.db.database import SessionLocal
from app.services.message_reprocessing_service import MessageReprocessingService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild normalized_messages and recommendations from immutable messages "
            "using parser version 2.0."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process every row and print results, then roll back all changes.",
    )
    parser.add_argument("--start-message-id", type=int)
    parser.add_argument("--end-message-id", type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    db = SessionLocal()
    try:
        summary = MessageReprocessingService(db).reprocess_all(
            dry_run=args.dry_run,
            start_message_id=args.start_message_id,
            end_message_id=args.end_message_id,
        )
        print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
        print("DRY RUN: database changes were rolled back." if args.dry_run else "Reprocessing committed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()