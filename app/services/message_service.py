from sqlalchemy.orm import Session

from app.models.message import Message


def save_message(
    db: Session,
    source_id: int,
    telegram_message,
    tags: list[str],
):
    message = Message(
        source_id=source_id,
        external_message_id=telegram_message.id,
        message_date=telegram_message.date,
        message_text=telegram_message.message,
        tags=tags,
        raw_json=telegram_message.to_dict(),
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message