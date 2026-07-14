from __future__ import annotations

from collections import defaultdict
from datetime import date
from statistics import mean, median
from typing import Any, Callable, Iterable

from sqlalchemy.orm import Session

from app.analytics.field_resolver import (
    CHANNEL_FIELD_ALIASES,
    MESSAGE_FIELD_ALIASES,
    NORMALIZED_MESSAGE_FIELD_ALIASES,
    normalize_text,
    parse_targets,
    resolve_field,
    resolve_value,
    to_bool,
    to_date,
    to_datetime,
    to_float,
    to_int,
)
from app.analytics.records import AnalyticsMetricSummary, RecommendationAnalyticsRecord
from app.models.channel import Channel
from app.models.message import Message
from app.models.recommendation import Recommendation

try:
    from app.models.normalized_message import NormalizedMessage
except ImportError:  # Backward-compatible with projects that named the module differently.
    NormalizedMessage = None  # type: ignore[assignment,misc]


class AnalyticsService:
    """Read-only analytics over the existing InsightHub ORM models."""

    def __init__(self, db: Session):
        self.db = db

    def load_records(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        symbol: str | None = None,
        channel: str | None = None,
        status: str | None = None,
    ) -> list[RecommendationAnalyticsRecord]:
        recommendations = self.db.query(Recommendation).all()
        messages = self.db.query(Message).all()
        channels = self.db.query(Channel).all()

        message_by_id = {
            resolve_value(message, MESSAGE_FIELD_ALIASES["id"]): message
            for message in messages
        }
        channel_by_id = {
            resolve_value(channel_obj, CHANNEL_FIELD_ALIASES["id"]): channel_obj
            for channel_obj in channels
        }
        normalized_by_message_id = self._load_normalized_messages()

        records: list[RecommendationAnalyticsRecord] = []
        for recommendation in recommendations:
            message_id = to_int(resolve_field(recommendation, "message_id"))
            message = message_by_id.get(message_id)
            channel_id = to_int(
                resolve_value(message, MESSAGE_FIELD_ALIASES["channel_id"])
            )
            channel_obj = channel_by_id.get(channel_id)
            signal_date = to_date(
                resolve_value(message, MESSAGE_FIELD_ALIASES["signal_date"])
            )

            target1 = to_float(resolve_field(recommendation, "target1"))
            target2 = to_float(resolve_field(recommendation, "target2"))
            target3 = to_float(resolve_field(recommendation, "target3"))
            targets = parse_targets(
                resolve_field(recommendation, "targets_json"),
                target1,
                target2,
                target3,
            )

            normalized_message = normalized_by_message_id.get(message_id)
            record = RecommendationAnalyticsRecord(
                recommendation_id=to_int(resolve_field(recommendation, "id")) or 0,
                message_id=message_id,
                channel_id=channel_id,
                channel_name=normalize_text(
                    resolve_value(channel_obj, CHANNEL_FIELD_ALIASES["channel_name"])
                ),
                signal_date=signal_date,
                symbol=normalize_text(resolve_field(recommendation, "symbol")),
                action=normalize_text(resolve_field(recommendation, "action")),
                entry_low=to_float(resolve_field(recommendation, "entry_low")),
                entry_high=to_float(resolve_field(recommendation, "entry_high")),
                stop_loss=to_float(resolve_field(recommendation, "stop_loss")),
                target1=target1,
                target2=target2,
                target3=target3,
                targets=targets,
                pattern=normalize_text(resolve_field(recommendation, "pattern")),
                risk=normalize_text(resolve_field(recommendation, "risk")),
                lifecycle_status=normalize_text(
                    resolve_field(recommendation, "lifecycle_status")
                ),
                current_price=to_float(
                    resolve_field(recommendation, "current_price")
                ),
                current_return_pct=to_float(
                    resolve_field(recommendation, "current_return_pct")
                ),
                max_return_pct=to_float(
                    resolve_field(recommendation, "max_return_pct")
                ),
                min_return_pct=to_float(
                    resolve_field(recommendation, "min_return_pct")
                ),
                target_hit=to_bool(resolve_field(recommendation, "target_hit")),
                target_hit_level=to_int(
                    resolve_field(recommendation, "target_hit_level")
                ),
                target_hit_date=to_date(
                    resolve_field(recommendation, "target_hit_date")
                ),
                stop_loss_hit=to_bool(
                    resolve_field(recommendation, "stop_loss_hit")
                ),
                stop_loss_hit_date=to_date(
                    resolve_field(recommendation, "stop_loss_hit_date")
                ),
                days_to_target=to_int(
                    resolve_field(recommendation, "days_to_target")
                ),
                days_to_stop_loss=to_int(
                    resolve_field(recommendation, "days_to_stop_loss")
                ),
                evaluated_through=to_date(
                    resolve_field(recommendation, "evaluated_through")
                ),
                performance_calculated_at=to_datetime(
                    resolve_field(recommendation, "performance_calculated_at")
                ),
                normalized_text=normalize_text(
                    resolve_value(
                        normalized_message,
                        NORMALIZED_MESSAGE_FIELD_ALIASES["normalized_text"],
                    )
                ),
                raw_message_text=normalize_text(
                    resolve_value(
                        message,
                        MESSAGE_FIELD_ALIASES["raw_message_text"],
                    )
                ),
            )

            if self._matches_filters(
                record,
                start_date=start_date,
                end_date=end_date,
                symbol=symbol,
                channel=channel,
                status=status,
            ):
                records.append(record)

        records.sort(
            key=lambda item: (
                item.signal_date or date.min,
                item.recommendation_id,
            ),
            reverse=True,
        )
        return records

    def summarize(
        self,
        records: Iterable[RecommendationAnalyticsRecord],
    ) -> AnalyticsMetricSummary:
        rows = list(records)
        rows_with_performance = [row for row in rows if row.has_performance]
        closed_rows = [row for row in rows if row.is_closed]
        wins = [row for row in closed_rows if row.is_win]
        losses = [row for row in closed_rows if row.is_loss]
        target_hits = [row for row in rows if row.target_hit]
        stop_loss_hits = [row for row in rows if row.stop_loss_hit]

        current_returns = self._numbers(
            row.current_return_pct for row in rows_with_performance
        )
        max_returns = self._numbers(
            row.max_return_pct for row in rows_with_performance
        )
        profitable = [value for value in current_returns if value > 0]
        unprofitable = [value for value in current_returns if value < 0]
        target_days = self._numbers(row.days_to_target for row in target_hits)
        stop_days = self._numbers(row.days_to_stop_loss for row in stop_loss_hits)

        resolved_outcomes = len(wins) + len(losses)
        return AnalyticsMetricSummary(
            total_recommendations=len(rows),
            recommendations_with_performance=len(rows_with_performance),
            open_recommendations=sum(1 for row in rows if row.is_open),
            closed_recommendations=len(closed_rows),
            wins=len(wins),
            losses=len(losses),
            target_hits=len(target_hits),
            stop_loss_hits=len(stop_loss_hits),
            profitable_recommendations=len(profitable),
            unprofitable_recommendations=len(unprofitable),
            win_rate_pct=self._percentage(len(wins), resolved_outcomes),
            target_hit_rate_pct=self._percentage(len(target_hits), len(rows_with_performance)),
            stop_loss_rate_pct=self._percentage(
                len(stop_loss_hits), len(rows_with_performance)
            ),
            profitable_rate_pct=self._percentage(
                len(profitable), len(current_returns)
            ),
            average_current_return_pct=self._average(current_returns),
            median_current_return_pct=self._median(current_returns),
            average_max_return_pct=self._average(max_returns),
            median_max_return_pct=self._median(max_returns),
            best_current_return_pct=max(current_returns) if current_returns else None,
            worst_current_return_pct=min(current_returns) if current_returns else None,
            best_max_return_pct=max(max_returns) if max_returns else None,
            average_days_to_target=self._average(target_days),
            average_days_to_stop_loss=self._average(stop_days),
        )

    def group_metrics(
        self,
        records: Iterable[RecommendationAnalyticsRecord],
        group_by: str,
        minimum_sample_size: int = 1,
    ) -> list[dict[str, Any]]:
        groupers: dict[str, Callable[[RecommendationAnalyticsRecord], str]] = {
            "symbol": lambda row: row.symbol or "UNKNOWN",
            "channel": lambda row: row.channel_name or "UNKNOWN",
            "pattern": lambda row: row.pattern or "UNKNOWN",
            "action": lambda row: row.action or "UNKNOWN",
            "risk": lambda row: row.risk or "UNKNOWN",
            "status": lambda row: row.lifecycle_status or "UNKNOWN",
            "month": lambda row: (
                row.signal_date.strftime("%Y-%m") if row.signal_date else "UNKNOWN"
            ),
            "year": lambda row: (
                str(row.signal_date.year) if row.signal_date else "UNKNOWN"
            ),
        }
        if group_by not in groupers:
            allowed = ", ".join(sorted(groupers))
            raise ValueError(f"Unsupported group_by '{group_by}'. Allowed: {allowed}")

        grouped: dict[str, list[RecommendationAnalyticsRecord]] = defaultdict(list)
        for row in records:
            grouped[groupers[group_by](row)].append(row)

        output: list[dict[str, Any]] = []
        for key, group_rows in grouped.items():
            if len(group_rows) < minimum_sample_size:
                continue
            metrics = self.summarize(group_rows).to_dict()
            metrics["group_by"] = group_by
            metrics["group_value"] = key
            metrics["sample_size_warning"] = len(group_rows) < 5
            output.append(metrics)

        output.sort(
            key=lambda item: (
                item.get("win_rate_pct") is not None,
                item.get("win_rate_pct") or -1,
                item.get("average_current_return_pct") or -999999,
                item.get("total_recommendations") or 0,
            ),
            reverse=True,
        )
        return output

    def doubled_within_months(
        self,
        records: Iterable[RecommendationAnalyticsRecord],
        months: int,
    ) -> list[RecommendationAnalyticsRecord]:
        if months <= 0:
            raise ValueError("months must be greater than zero")
        maximum_days = round(months * 30.4375)
        result: list[RecommendationAnalyticsRecord] = []
        for row in records:
            days_to_target = row.days_to_target
            if (
                days_to_target is None
                and row.signal_date is not None
                and row.target_hit_date is not None
            ):
                days_to_target = (row.target_hit_date - row.signal_date).days
            if (
                row.max_return_pct is not None
                and row.max_return_pct >= 100.0
                and days_to_target is not None
                and 0 <= days_to_target <= maximum_days
            ):
                result.append(row)
        return sorted(
            result,
            key=lambda row: row.max_return_pct or 0,
            reverse=True,
        )

    def recommendations_above_return(
        self,
        records: Iterable[RecommendationAnalyticsRecord],
        minimum_return_pct: float,
    ) -> list[RecommendationAnalyticsRecord]:
        return sorted(
            [
                row
                for row in records
                if row.max_return_pct is not None
                and row.max_return_pct >= minimum_return_pct
            ],
            key=lambda row: row.max_return_pct or 0,
            reverse=True,
        )

    def stale_open_recommendations(
        self,
        records: Iterable[RecommendationAnalyticsRecord],
        as_of_date: date,
        older_than_days: int,
    ) -> list[RecommendationAnalyticsRecord]:
        if older_than_days < 0:
            raise ValueError("older_than_days cannot be negative")
        return sorted(
            [
                row
                for row in records
                if row.is_open
                and row.signal_date is not None
                and (as_of_date - row.signal_date).days > older_than_days
            ],
            key=lambda row: row.signal_date or date.min,
        )

    def target_level_report(
        self,
        records: Iterable[RecommendationAnalyticsRecord],
    ) -> list[dict[str, Any]]:
        rows = list(records)
        return [
            {
                "target_level": level,
                "hit_count": sum(
                    1
                    for row in rows
                    if row.target_hit
                    and (row.target_hit_level or 1) >= level
                ),
                "eligible_count": sum(
                    1 for row in rows if len(row.targets) >= level
                ),
                "hit_rate_pct": self._percentage(
                    sum(
                        1
                        for row in rows
                        if row.target_hit
                        and (row.target_hit_level or 1) >= level
                    ),
                    sum(1 for row in rows if len(row.targets) >= level),
                ),
            }
            for level in (1, 2, 3)
        ]

    def _load_normalized_messages(self) -> dict[int, Any]:
        if NormalizedMessage is None:
            return {}
        try:
            normalized_rows = self.db.query(NormalizedMessage).all()
        except Exception:
            return {}
        result: dict[int, Any] = {}
        for row in normalized_rows:
            message_id = to_int(
                resolve_value(
                    row,
                    NORMALIZED_MESSAGE_FIELD_ALIASES["message_id"],
                )
            )
            if message_id is not None:
                result[message_id] = row
        return result

    @staticmethod
    def _matches_filters(
        record: RecommendationAnalyticsRecord,
        start_date: date | None,
        end_date: date | None,
        symbol: str | None,
        channel: str | None,
        status: str | None,
    ) -> bool:
        if start_date and (record.signal_date is None or record.signal_date < start_date):
            return False
        if end_date and (record.signal_date is None or record.signal_date > end_date):
            return False
        if symbol and (record.symbol or "").upper() != symbol.upper():
            return False
        if channel and channel.lower() not in (record.channel_name or "").lower():
            return False
        if status and (record.lifecycle_status or "").lower() != status.lower():
            return False
        return True

    @staticmethod
    def _numbers(values: Iterable[float | int | None]) -> list[float]:
        return [float(value) for value in values if value is not None]

    @staticmethod
    def _percentage(numerator: int, denominator: int) -> float | None:
        if denominator == 0:
            return None
        return round((numerator / denominator) * 100.0, 2)

    @staticmethod
    def _average(values: list[float]) -> float | None:
        return round(mean(values), 2) if values else None

    @staticmethod
    def _median(values: list[float]) -> float | None:
        return round(median(values), 2) if values else None
