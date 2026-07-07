from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.services.parser import parse_recommendation


def save_recommendation(db: Session, message):
    """
    message is a Messages model instance from Sprint 1.
    """

    parsed = parse_recommendation(message.raw_text)

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

    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)

    return recommendation