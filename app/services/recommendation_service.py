from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.parsers.recommendation_parser import ParsedRecommendation


def save_recommendation(
    db: Session,
    message_id: int,
    parsed: ParsedRecommendation | dict[str, Any],
) -> Recommendation:
    values = (
        parsed.to_dict()
        if isinstance(parsed, ParsedRecommendation)
        else parsed
    )

    recommendation = (
        db.query(Recommendation)
        .filter(Recommendation.message_id == message_id)
        .one_or_none()
    )
    if recommendation is None:
        recommendation = Recommendation(message_id=message_id)
        db.add(recommendation)

    recommendation.symbol = values.get("symbol")
    recommendation.action = values.get("action")
    recommendation.entry_low = values.get("entry_low")
    recommendation.entry_high = values.get("entry_high")
    recommendation.entry_instruction = (
        values.get("entry_instruction") or "UNSPECIFIED"
    )
    recommendation.entry_instruction_text = values.get(
        "entry_instruction_text"
    )
    recommendation.entry_price_source = (
        values.get("entry_price_source") or "MESSAGE"
    )
    recommendation.entry_price_timestamp = values.get(
        "entry_price_timestamp"
    )
    recommendation.stop_loss = values.get("stop_loss")
    recommendation.support_level = values.get("support_level")
    recommendation.trigger_level = values.get("trigger_level")
    recommendation.target1 = values.get("target1")
    recommendation.target2 = values.get("target2")
    recommendation.target3 = values.get("target3")
    recommendation.pattern = values.get("pattern")
    recommendation.risk = values.get("risk")

    targets = values.get("targets_json") or {
        "target_type": "UNSPECIFIED",
        "targets": [],
    }
    recommendation.targets_json = (
        targets
        if isinstance(targets, str)
        else json.dumps(targets, sort_keys=True)
    )

    db.flush()
    return recommendation