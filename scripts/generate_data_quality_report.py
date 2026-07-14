from __future__ import annotations

try:
    import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import scripts._bootstrap  # noqa: F401

import argparse
from pathlib import Path

from app.db.database import SessionLocal
from app.services.analytics_service import AnalyticsService
from app.services.data_quality_service import DataQualityService
from app.services.recommendation_export_service import RecommendationExportService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate InsightHub Sprint 5 data-quality and price-coverage reports."
    )
    parser.add_argument("--output-dir", default="output/sprint5/data_quality")
    parser.add_argument("--long-gap-business-days", type=int, default=5)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        analytics = AnalyticsService(db)
        quality = DataQualityService(db)
        exporter = RecommendationExportService()

        records = analytics.load_records()
        issues = quality.recommendation_issues(records)
        issue_summary = quality.issue_summary(issues)
        coverage = quality.market_price_coverage(
            records,
            long_gap_business_days=args.long_gap_business_days,
        )

        exporter.write_csv(output_dir / "recommendation_issues.csv", issues)
        exporter.write_json(output_dir / "recommendation_issues.json", issues)
        exporter.write_csv(output_dir / "issue_summary.csv", issue_summary)
        exporter.write_json(output_dir / "issue_summary.json", issue_summary)
        exporter.write_csv(output_dir / "market_price_coverage.csv", coverage)
        exporter.write_json(output_dir / "market_price_coverage.json", coverage)

        print("\nInsightHub Sprint 5 Data Quality")
        print("=" * 37)
        print(f"Recommendations checked: {len(records)}")
        print(f"Issues found: {len(issues)}")
        for row in issue_summary:
            print(f"{row['severity']} {row['issue_type']}: {row['count']}")
        missing_prices = sum(1 for row in coverage if row["price_row_count"] == 0)
        missing_forward = sum(
            1 for row in coverage if not row["has_forward_price_history"]
        )
        print(f"Recommendations with no symbol price history: {missing_prices}")
        print(f"Recommendations without forward price history: {missing_forward}")
        print(f"Reports written to: {output_dir.resolve()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()