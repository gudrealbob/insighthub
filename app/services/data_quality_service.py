from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.analytics.records import RecommendationAnalyticsRecord
from app.models.market_price import MarketPrice


class DataQualityService:
    """Read-only checks for recommendation and market-price analytics quality."""

    def __init__(self, db: Session):
        self.db = db

    def recommendation_issues(
        self,
        records: Iterable[RecommendationAnalyticsRecord],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for row in records:
            self._append_missing_field_issues(row, issues)
            self._append_price_logic_issues(row, issues)
            self._append_performance_issues(row, issues)
        return sorted(
            issues,
            key=lambda item: (
                item["severity"],
                item["issue_type"],
                item["recommendation_id"],
            ),
        )

    def market_price_coverage(
        self,
        records: Iterable[RecommendationAnalyticsRecord],
        long_gap_business_days: int = 5,
    ) -> list[dict[str, Any]]:
        price_rows = self.db.query(MarketPrice).all()
        dates_by_symbol: dict[str, set[date]] = defaultdict(set)

        for price_row in price_rows:
            symbol = str(getattr(price_row, "symbol", "") or "").upper().strip()
            price_date = getattr(price_row, "price_date", None)
            if symbol and isinstance(price_date, date):
                dates_by_symbol[symbol].add(price_date)

        coverage: list[dict[str, Any]] = []
        for row in records:
            symbol = (row.symbol or "").upper().strip()
            price_dates = sorted(dates_by_symbol.get(symbol, set()))
            min_date = price_dates[0] if price_dates else None
            max_date = price_dates[-1] if price_dates else None
            signal_covered = bool(
                row.signal_date
                and min_date
                and max_date
                and min_date <= row.signal_date <= max_date
            )
            business_gap_count = self._count_long_business_gaps(
                price_dates,
                threshold=long_gap_business_days,
            )
            coverage.append(
                {
                    "recommendation_id": row.recommendation_id,
                    "message_id": row.message_id,
                    "symbol": row.symbol,
                    "signal_date": row.signal_date.isoformat()
                    if row.signal_date
                    else None,
                    "price_row_count": len(price_dates),
                    "first_price_date": min_date.isoformat() if min_date else None,
                    "latest_price_date": max_date.isoformat() if max_date else None,
                    "signal_date_covered": signal_covered,
                    "long_business_day_gap_count": business_gap_count,
                    "has_forward_price_history": bool(
                        row.signal_date and max_date and max_date >= row.signal_date
                    ),
                }
            )
        return coverage

    @staticmethod
    def issue_summary(issues: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        counts: dict[tuple[str, str], int] = defaultdict(int)
        for issue in issues:
            counts[(issue["severity"], issue["issue_type"])] += 1
        return [
            {
                "severity": severity,
                "issue_type": issue_type,
                "count": count,
            }
            for (severity, issue_type), count in sorted(counts.items())
        ]

    @staticmethod
    def _append_missing_field_issues(
        row: RecommendationAnalyticsRecord,
        issues: list[dict[str, Any]],
    ) -> None:
        if not row.symbol:
            DataQualityService._add_issue(
                issues, row, "ERROR", "MISSING_SYMBOL", "Symbol is null or blank."
            )
        if not row.action:
            DataQualityService._add_issue(
                issues, row, "ERROR", "MISSING_ACTION", "Action is null or blank."
            )
        if row.entry_low is None and row.entry_high is None:
            DataQualityService._add_issue(
                issues,
                row,
                "ERROR",
                "MISSING_ENTRY",
                "Both entry_low and entry_high are null.",
            )
        if row.message_id is None:
            DataQualityService._add_issue(
                issues,
                row,
                "ERROR",
                "MISSING_MESSAGE_REFERENCE",
                "Recommendation has no message_id.",
            )
        if row.signal_date is None:
            DataQualityService._add_issue(
                issues,
                row,
                "WARNING",
                "MISSING_SIGNAL_DATE",
                "The source message date could not be resolved.",
            )
        if not row.has_performance:
            DataQualityService._add_issue(
                issues,
                row,
                "WARNING",
                "MISSING_PERFORMANCE",
                "No calculated performance fields were found.",
            )

    @staticmethod
    def _append_price_logic_issues(
        row: RecommendationAnalyticsRecord,
        issues: list[dict[str, Any]],
    ) -> None:
        if (
            row.entry_low is not None
            and row.entry_high is not None
            and row.entry_low > row.entry_high
        ):
            DataQualityService._add_issue(
                issues,
                row,
                "ERROR",
                "INVALID_ENTRY_RANGE",
                "entry_low is greater than entry_high.",
            )

        entry_reference = row.entry_high or row.entry_low
        action = (row.action or "").upper()
        if action in {"BUY", "LONG"} and entry_reference is not None:
            if row.stop_loss is not None and row.stop_loss >= entry_reference:
                DataQualityService._add_issue(
                    issues,
                    row,
                    "ERROR",
                    "BUY_STOP_LOSS_NOT_BELOW_ENTRY",
                    "Buy/long stop loss is not below the entry reference.",
                )
            invalid_targets = [target for target in row.targets if target <= entry_reference]
            if invalid_targets:
                DataQualityService._add_issue(
                    issues,
                    row,
                    "ERROR",
                    "BUY_TARGET_NOT_ABOVE_ENTRY",
                    f"Targets at or below entry: {invalid_targets}",
                )

        if action in {"SELL", "SHORT"} and row.entry_low is not None:
            if row.stop_loss is not None and row.stop_loss <= row.entry_low:
                DataQualityService._add_issue(
                    issues,
                    row,
                    "ERROR",
                    "SELL_STOP_LOSS_NOT_ABOVE_ENTRY",
                    "Sell/short stop loss is not above the entry reference.",
                )
            invalid_targets = [target for target in row.targets if target >= row.entry_low]
            if invalid_targets:
                DataQualityService._add_issue(
                    issues,
                    row,
                    "ERROR",
                    "SELL_TARGET_NOT_BELOW_ENTRY",
                    f"Targets at or above entry: {invalid_targets}",
                )

        raw_targets = [
            value
            for value in (row.target1, row.target2, row.target3)
            if value is not None
        ]
        if len(raw_targets) != len(set(raw_targets)):
            DataQualityService._add_issue(
                issues,
                row,
                "WARNING",
                "DUPLICATE_TARGETS",
                "Two or more numbered target fields contain the same value.",
            )

    @staticmethod
    def _append_performance_issues(
        row: RecommendationAnalyticsRecord,
        issues: list[dict[str, Any]],
    ) -> None:
        if row.target_hit and row.stop_loss_hit:
            DataQualityService._add_issue(
                issues,
                row,
                "WARNING",
                "TARGET_AND_STOP_LOSS_BOTH_HIT",
                "Daily OHLCV cannot prove intraday hit order; review TD-008.",
            )
        if row.target_hit and row.target_hit_date is None:
            DataQualityService._add_issue(
                issues,
                row,
                "WARNING",
                "TARGET_HIT_DATE_MISSING",
                "Target is marked hit but target_hit_date is null.",
            )
        if row.stop_loss_hit and row.stop_loss_hit_date is None:
            DataQualityService._add_issue(
                issues,
                row,
                "WARNING",
                "STOP_LOSS_HIT_DATE_MISSING",
                "Stop loss is marked hit but stop_loss_hit_date is null.",
            )
        if row.target_hit_level is not None and row.target_hit_level not in {1, 2, 3}:
            DataQualityService._add_issue(
                issues,
                row,
                "WARNING",
                "INVALID_TARGET_HIT_LEVEL",
                "target_hit_level must be 1, 2, or 3.",
            )

    @staticmethod
    def _add_issue(
        issues: list[dict[str, Any]],
        row: RecommendationAnalyticsRecord,
        severity: str,
        issue_type: str,
        detail: str,
    ) -> None:
        issues.append(
            {
                "recommendation_id": row.recommendation_id,
                "message_id": row.message_id,
                "channel": row.channel_name,
                "symbol": row.symbol,
                "signal_date": row.signal_date.isoformat()
                if row.signal_date
                else None,
                "severity": severity,
                "issue_type": issue_type,
                "detail": detail,
            }
        )

    @staticmethod
    def _count_long_business_gaps(
        price_dates: list[date],
        threshold: int,
    ) -> int:
        if len(price_dates) < 2:
            return 0
        count = 0
        for previous, current in zip(price_dates, price_dates[1:]):
            business_days = 0
            cursor = previous + timedelta(days=1)
            while cursor < current:
                if cursor.weekday() < 5:
                    business_days += 1
                cursor += timedelta(days=1)
            if business_days >= threshold:
                count += 1
        return count
