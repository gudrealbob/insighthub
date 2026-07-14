from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


@dataclass(slots=True)
class RecommendationAnalyticsRecord:
    recommendation_id: int
    message_id: int | None
    channel_id: int | None
    channel_name: str | None
    signal_date: date | None
    symbol: str | None
    action: str | None
    entry_low: float | None
    entry_high: float | None
    stop_loss: float | None
    target1: float | None
    target2: float | None
    target3: float | None
    targets: list[float] = field(default_factory=list)
    pattern: str | None = None
    risk: str | None = None
    lifecycle_status: str | None = None
    current_price: float | None = None
    current_return_pct: float | None = None
    max_return_pct: float | None = None
    min_return_pct: float | None = None
    target_hit: bool = False
    target_hit_level: int | None = None
    target_hit_date: date | None = None
    stop_loss_hit: bool = False
    stop_loss_hit_date: date | None = None
    days_to_target: int | None = None
    days_to_stop_loss: int | None = None
    evaluated_through: date | None = None
    performance_calculated_at: datetime | None = None
    normalized_text: str | None = None
    raw_message_text: str | None = None

    @property
    def is_open(self) -> bool:
        status = (self.lifecycle_status or "").strip().lower()
        if self.target_hit or self.stop_loss_hit:
            return False
        return status in {"", "open", "active", "pending", "tracking", "in_progress"}

    @property
    def is_closed(self) -> bool:
        return not self.is_open

    @property
    def is_win(self) -> bool:
        status = (self.lifecycle_status or "").strip().lower()
        return self.target_hit or status in {
            "target_hit",
            "target_reached",
            "won",
            "win",
            "success",
            "closed_win",
        }

    @property
    def is_loss(self) -> bool:
        status = (self.lifecycle_status or "").strip().lower()
        return self.stop_loss_hit or status in {
            "stop_loss_hit",
            "sl_hit",
            "lost",
            "loss",
            "failed",
            "closed_loss",
        }

    @property
    def has_performance(self) -> bool:
        return any(
            value is not None
            for value in (
                self.current_price,
                self.current_return_pct,
                self.max_return_pct,
                self.min_return_pct,
                self.evaluated_through,
                self.performance_calculated_at,
            )
        ) or self.target_hit or self.stop_loss_hit

    def to_dict(self) -> dict[str, Any]:
        return _serialize_value(asdict(self))


@dataclass(slots=True)
class AnalyticsMetricSummary:
    total_recommendations: int
    recommendations_with_performance: int
    open_recommendations: int
    closed_recommendations: int
    wins: int
    losses: int
    target_hits: int
    stop_loss_hits: int
    profitable_recommendations: int
    unprofitable_recommendations: int
    win_rate_pct: float | None
    target_hit_rate_pct: float | None
    stop_loss_rate_pct: float | None
    profitable_rate_pct: float | None
    average_current_return_pct: float | None
    median_current_return_pct: float | None
    average_max_return_pct: float | None
    median_max_return_pct: float | None
    best_current_return_pct: float | None
    worst_current_return_pct: float | None
    best_max_return_pct: float | None
    average_days_to_target: float | None
    average_days_to_stop_loss: float | None

    def to_dict(self) -> dict[str, Any]:
        return _serialize_value(asdict(self))
