from app.services.parser import parse_recommendation
from app.models.recommendation import Recommendation


def save_recommendation(db, message):

    parsed = parse_recommendation(message.message_text)

    #
    # No recommendation detected
    #
    if not parsed:
        return None


    #
    # Ignore empty parser results
    #
    if not any(parsed.values()):
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
        return existing


    recommendation = Recommendation(
        message_id=message.id,
        symbol=parsed.get("symbol"),
        action=parsed.get("action"),
        entry_low=parsed.get("entry_low"),
        entry_high=parsed.get("entry_high"),
        stop_loss=parsed.get("stop_loss"),
        target1=parsed.get("target1"),
        target2=parsed.get("target2"),
        target3=parsed.get("target3"),
        pattern=parsed.get("pattern"),
        risk=parsed.get("risk"),
    )


    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)


    return recommendation