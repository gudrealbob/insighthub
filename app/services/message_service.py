import json

from sqlalchemy.orm import Session
from app.models.message import Message


def json_serializable(obj):
    if hasattr(obj, "isoformat"):
        return obj.isoformat()

    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")

    if hasattr(obj, "__dict__"):
        return str(obj)

    return str(obj)

def save_message(
    db,
    channel_id,
    telegram_message,
    tags,
):
    existing_message = (
        db.query(Message)
        .filter(
            Message.channel_id == channel_id,
            Message.external_message_id == telegram_message.id,
        )
        .first()
    )

    if existing_message:
        return existing_message

    message = Message(
        channel_id=channel_id,
        external_message_id=telegram_message.id,
        message_date=telegram_message.date,
        message_text=telegram_message.message,
        tags=tags,
        raw_json=json.loads(
            json.dumps(
                telegram_message.to_dict(),
                default=json_serializable
            )
        ),
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message