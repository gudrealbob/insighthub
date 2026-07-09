from app.models.normalized_message import NormalizedMessage
from app.models.recommendation import Recommendation
from app.services.parser import parse_recommendation


def save_recommendation(db, message):
    normalized = (
        db.query(NormalizedMessage)
        .filter(
            NormalizedMessage.message_id == message.id
        )
        .first()
    )

    #
    # Message not normalized
    #
    if normalized is None:
        return None

    parsed = parse_recommendation(
        clean_text=normalized.clean_text or "",
        symbol=normalized.symbol,
        action=normalized.action,
    )

    #
    # No recommendation detected
    #
    if not parsed:
        return None

    #
    # Ignore empty parser results
    #
    #
    # Business validation
    #
    required_fields = (
        parsed.get("symbol"),
        parsed.get("action"),
        parsed.get("entry_low"),
    )

    if not all(required_fields):
        normalized.parser_status = "FAILED"

        db.commit()

        return None

    #
    # Prevent duplicate recommendation creation
    #
    existing = (
        db.query(Recommendation)
        .filter(
            Recommendation.message_id == message.id
        )
        .first()
    )

    if existing:
        existing.symbol = parsed["symbol"]
        existing.action = parsed["action"]
        existing.entry_low = parsed["entry_low"]
        existing.entry_high = parsed["entry_high"]
        existing.stop_loss = parsed["stop_loss"]
        existing.target1 = parsed["target1"]
        existing.target2 = parsed["target2"]
        existing.target3 = parsed["target3"]
        existing.pattern = parsed["pattern"]
        existing.risk = parsed["risk"]

        normalized.parser_status = "SUCCESS"

        db.commit()
        db.refresh(existing)

        return existing

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
        pattern=parsed["pattern"],
        risk=parsed["risk"],
    )

    normalized.parser_status = "SUCCESS"
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)

    return recommendation