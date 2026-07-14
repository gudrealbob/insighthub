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
        description="Generate InsightHub Sprint 5 recommendation analytics reports."
    )
    parser.add_argument("--output-dir", default="output/sprint5/analytics")
    parser.add_argument("--start-date", help="Inclusive YYYY-MM-DD")
    parser.add_argument("--end-date", help="Inclusive YYYY-MM-DD")
    parser.add_argument("--symbol")
    parser.add_argument("--channel")
    parser.add_argument("--status")
    parser.add_argument("--minimum-sample-size", type=int, default=1)
    parser.add_argument("--doubled-within-months", type=int, default=12)
    parser.add_argument("--minimum-return-pct", type=float, default=10.0)
    parser.add_argument("--stale-open-days", type=int, default=90)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        service = AnalyticsService(db)
        exporter = RecommendationExportService()
        records = service.load_records(
            start_date=parse_date(args.start_date),
            end_date=parse_date(args.end_date),
            symbol=args.symbol,
            channel=args.channel,
            status=args.status,
        )
        summary = service.summarize(records)

        exporter.write_json(output_dir / "summary.json", [summary.to_dict()])
        exporter.write_csv(output_dir / "summary.csv", [summary.to_dict()])

        for group_by in (
            "channel",
            "pattern",
            "symbol",
            "action",
            "risk",
            "status",
            "month",
            "year",
        ):
            rows = service.group_metrics(
                records,
                group_by=group_by,
                minimum_sample_size=args.minimum_sample_size,
            )
            exporter.write_csv(output_dir / f"analytics_by_{group_by}.csv", rows)
            exporter.write_json(output_dir / f"analytics_by_{group_by}.json", rows)

        doubled = service.doubled_within_months(
            records,
            months=args.doubled_within_months,
        )
        exporter.write_csv(
            output_dir / "recommendations_doubled.csv",
            [row.to_dict() for row in doubled],
        )

        above_return = service.recommendations_above_return(
            records,
            minimum_return_pct=args.minimum_return_pct,
        )
        exporter.write_csv(
            output_dir / "recommendations_above_return.csv",
            [row.to_dict() for row in above_return],
        )

        stale_open = service.stale_open_recommendations(
            records,
            as_of_date=date.today(),
            older_than_days=args.stale_open_days,
        )
        exporter.write_csv(
            output_dir / "stale_open_recommendations.csv",
            [row.to_dict() for row in stale_open],
        )

        target_levels = service.target_level_report(records)
        exporter.write_csv(output_dir / "target_level_report.csv", target_levels)
        exporter.write_json(output_dir / "target_level_report.json", target_levels)

        print("\nInsightHub Sprint 5 Analytics")
        print("=" * 34)
        for key, value in summary.to_dict().items():
            print(f"{key}: {value}")
        print(f"\nDoubled within {args.doubled_within_months} months: {len(doubled)}")
        print(f"Reached at least {args.minimum_return_pct}%: {len(above_return)}")
        print(f"Open longer than {args.stale_open_days} days: {len(stale_open)}")
        print(f"Reports written to: {output_dir.resolve()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()