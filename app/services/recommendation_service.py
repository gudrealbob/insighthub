from sqlalchemy.exc import IntegrityError

from app.models.normalized_message import NormalizedMessage
from app.models.recommendation import Recommendation
from app.services.parser import parse_recommendation


def is_valid_recommendation(parsed):
    required_fields = (
        parsed.get("symbol"),
        parsed.get("action"),
        parsed.get("entry_low"),
    )

    return all(required_fields)


def save_recommendation(db, message):
    existing = (
        db.query(Recommendation)
        .filter(
            Recommendation.message_id == message.id
        )
        .first()
    )

    if existing:
        return existing

    normalized = (
        db.query(NormalizedMessage)
        .filter(
            NormalizedMessage.message_id == message.id
        )
        .first()
    )

    if normalized is None:
        return None

    parsed = parse_recommendation(
        clean_text=normalized.clean_text or "",
        symbol=normalized.symbol,
        action=normalized.action,
    )

    if not parsed:
        normalized.parser_status = "FAILED"
        db.commit()
        return None

    if not is_valid_recommendation(parsed):
        normalized.parser_status = "FAILED"
        db.commit()
        return None

    recommendation = Recommendation(
        message_id=message.id,
        symbol=parsed["symbol"],
        action=parsed["action"],
        entry_low=parsed["entry_low"],
        entry_high=parsed["entry_high"],
        stop_loss=parsed["stop_loss"],
        target1=parsed["target1"],
        target2=parsed["target2"],
        target3=parsed["target3"],
        targets_json=parsed["targets_json"],
        pattern=parsed["pattern"],
        risk=parsed["risk"],
    )

    normalized.parser_status = "SUCCESS"

    try:
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)

        return recommendation

    except IntegrityError:
        db.rollback()

        existing = (
            db.query(Recommendation)
            .filter(
                Recommendation.message_id == message.id
            )
            .first()
        )

        return existing