from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable


RECOMMENDATION_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "id": ("id",),
    "message_id": ("message_id",),
    "symbol": ("symbol", "ticker"),
    "action": ("action", "buy_sell", "side"),
    "entry_low": ("entry_low", "entry_price", "entry"),
    "entry_high": ("entry_high",),
    "stop_loss": ("stop_loss", "sl"),
    "target1": ("target1", "target_1"),
    "target2": ("target2", "target_2"),
    "target3": ("target3", "target_3"),
    "targets_json": ("targets_json", "targets"),
    "pattern": ("pattern", "chart_pattern"),
    "risk": ("risk", "risk_level"),
    "lifecycle_status": (
        "lifecycle_status",
        "status",
        "performance_status",
        "outcome",
    ),
    "current_price": ("current_price", "latest_price", "last_price"),
    "current_return_pct": (
        "current_return_pct",
        "return_pct",
        "current_profit_pct",
    ),
    "max_return_pct": (
        "max_return_pct",
        "maximum_return_pct",
        "max_gain_pct",
        "max_profit_pct",
    ),
    "min_return_pct": (
        "min_return_pct",
        "minimum_return_pct",
        "max_drawdown_pct",
        "maximum_drawdown_pct",
    ),
    "target_hit": ("target_hit", "is_target_hit", "target_reached"),
    "target_hit_level": (
        "target_hit_level",
        "highest_target_hit",
        "target_level_reached",
    ),
    "target_hit_date": ("target_hit_date", "target_reached_date"),
    "stop_loss_hit": ("stop_loss_hit", "sl_hit", "is_stop_loss_hit"),
    "stop_loss_hit_date": ("stop_loss_hit_date", "sl_hit_date"),
    "days_to_target": ("days_to_target", "target_days"),
    "days_to_stop_loss": ("days_to_stop_loss", "stop_loss_days", "sl_days"),
    "evaluated_through": (
        "evaluated_through",
        "performance_as_of_date",
        "last_evaluated_date",
    ),
    "performance_calculated_at": (
        "performance_calculated_at",
        "performance_updated_at",
        "calculated_at",
    ),
}

MESSAGE_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "id": ("id",),
    "channel_id": ("channel_id",),
    "signal_date": ("message_date", "posted_at", "created_at"),
    "raw_message_text": ("message_text", "raw_text", "text"),
}

CHANNEL_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "id": ("id",),
    "channel_name": ("name", "title", "username", "channel_name"),
}

NORMALIZED_MESSAGE_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "message_id": ("message_id",),
    "normalized_text": (
        "normalized_text",
        "clean_text",
        "curated_text",
        "message_text",
    ),
}


def resolve_value(obj: Any, aliases: Iterable[str], default: Any = None) -> Any:
    if obj is None:
        return default
    for name in aliases:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value
    return default


def resolve_field(obj: Any, field_name: str, default: Any = None) -> Any:
    aliases = RECOMMENDATION_FIELD_ALIASES[field_name]
    return resolve_value(obj, aliases, default)


def to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    try:
        normalized = str(value).strip().replace(",", "").replace("%", "")
        return float(Decimal(normalized))
    except (InvalidOperation, ValueError, TypeError):
        return None


def to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        number = to_float(value)
        return int(number) if number is not None else None


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float, Decimal)):
        return bool(value)
    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "hit",
        "reached",
    }


def to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_targets(
    targets_json: Any,
    target1: Any,
    target2: Any,
    target3: Any,
) -> list[float]:
    raw_targets: list[Any] = []

    if isinstance(targets_json, str):
        text = targets_json.strip()
        if text:
            try:
                decoded = json.loads(text)
                if isinstance(decoded, list):
                    raw_targets.extend(decoded)
                elif decoded is not None:
                    raw_targets.append(decoded)
            except json.JSONDecodeError:
                raw_targets.extend(part.strip() for part in text.split(","))
    elif isinstance(targets_json, list):
        raw_targets.extend(targets_json)
    elif targets_json is not None:
        raw_targets.append(targets_json)

    raw_targets.extend([target1, target2, target3])

    parsed: list[float] = []
    for raw_target in raw_targets:
        if isinstance(raw_target, dict):
            raw_target = (
                raw_target.get("price")
                or raw_target.get("target")
                or raw_target.get("value")
            )
        number = to_float(raw_target)
        if number is not None and number not in parsed:
            parsed.append(number)

    return parsed