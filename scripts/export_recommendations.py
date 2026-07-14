from __future__ import annotations

try:
    import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import scripts._bootstrap  # noqa: F401

import argparse
from datetime import date
from pathlib import Path

from app.db.database import SessionLocal
from app.services.analytics_service import AnalyticsService
from app.services.recommendation_export_service import RecommendationExportService


def parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export InsightHub recommendations for analysis and future RAG."
    )
    parser.add_argument("--output-dir", default="output/sprint5/export")
    parser.add_argument("--start-date", help="Inclusive YYYY-MM-DD")
    parser.add_argument("--end-date", help="Inclusive YYYY-MM-DD")
    parser.add_argument("--symbol")
    parser.add_argument("--channel")
    parser.add_argument("--status")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    db = SessionLocal()
    try:
        analytics = AnalyticsService(db)
        exporter = RecommendationExportService()
        records = analytics.load_records(
            start_date=parse_date(args.start_date),
            end_date=parse_date(args.end_date),
            symbol=args.symbol,
            channel=args.channel,
            status=args.status,
        )
        csv_path, json_path, jsonl_path = exporter.export_recommendations(
            Path(args.output_dir),
            records,
        )
        print(f"Exported {len(records)} recommendations")
        print(f"CSV: {csv_path.resolve()}")
        print(f"JSON: {json_path.resolve()}")
        print(f"RAG-ready JSONL: {jsonl_path.resolve()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
