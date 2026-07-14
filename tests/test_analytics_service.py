from datetime import date

from app.analytics.records import RecommendationAnalyticsRecord
from app.services.analytics_service import AnalyticsService


def make_record(
    recommendation_id: int,
    *,
    status: str,
    current_return_pct: float,
    max_return_pct: float,
    target_hit: bool = False,
    stop_loss_hit: bool = False,
    pattern: str = "Cup and Handle",
) -> RecommendationAnalyticsRecord:
    return RecommendationAnalyticsRecord(
        recommendation_id=recommendation_id,
        message_id=recommendation_id,
        channel_id=1,
        channel_name="Test Channel",
        signal_date=date(2026, 1, recommendation_id),
        symbol="TEST",
        action="BUY",
        entry_low=100.0,
        entry_high=101.0,
        stop_loss=95.0,
        target1=110.0,
        target2=120.0,
        target3=None,
        targets=[110.0, 120.0],
        pattern=pattern,
        risk="Medium",
        lifecycle_status=status,
        current_price=100.0 + current_return_pct,
        current_return_pct=current_return_pct,
        max_return_pct=max_return_pct,
        min_return_pct=-5.0,
        target_hit=target_hit,
        stop_loss_hit=stop_loss_hit,
        evaluated_through=date(2026, 2, 1),
    )


def test_summary_calculates_target_based_win_rate() -> None:
    service = AnalyticsService(db=None)  # type: ignore[arg-type]
    records = [
        make_record(1, status="target_hit", current_return_pct=10, max_return_pct=20, target_hit=True),
        make_record(2, status="stop_loss_hit", current_return_pct=-5, max_return_pct=3, stop_loss_hit=True),
        make_record(3, status="open", current_return_pct=2, max_return_pct=8),
    ]

    summary = service.summarize(records)

    assert summary.total_recommendations == 3
    assert summary.open_recommendations == 1
    assert summary.closed_recommendations == 2
    assert summary.wins == 1
    assert summary.losses == 1
    assert summary.win_rate_pct == 50.0
    assert summary.average_current_return_pct == 2.33


def test_group_metrics_groups_by_pattern() -> None:
    service = AnalyticsService(db=None)  # type: ignore[arg-type]
    records = [
        make_record(1, status="target_hit", current_return_pct=10, max_return_pct=20, target_hit=True),
        make_record(2, status="target_hit", current_return_pct=12, max_return_pct=25, target_hit=True),
        make_record(3, status="open", current_return_pct=1, max_return_pct=4, pattern="Flag"),
    ]

    groups = service.group_metrics(records, group_by="pattern")

    assert groups[0]["group_value"] == "Cup and Handle"
    assert groups[0]["total_recommendations"] == 2
    assert groups[0]["win_rate_pct"] == 100.0


def test_doubled_within_months() -> None:
    service = AnalyticsService(db=None)  # type: ignore[arg-type]
    fast_double = make_record(
        1,
        status="target_hit",
        current_return_pct=105,
        max_return_pct=120,
        target_hit=True,
    )
    fast_double.days_to_target = 100
    slow_double = make_record(
        2,
        status="target_hit",
        current_return_pct=110,
        max_return_pct=150,
        target_hit=True,
    )
    slow_double.days_to_target = 500

    result = service.doubled_within_months([fast_double, slow_double], months=6)

    assert [row.recommendation_id for row in result] == [1]