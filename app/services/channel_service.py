from telethon.tl.custom.message import Message
from sqlalchemy.orm import Session

from app.models.channel import Channel


def update_checkpoint(
    db: Session,
    channel: Channel,
    telegram_message: Message,
):

    channel.last_message_id = telegram_message.id
    channel.last_message_date = telegram_message.date

    db.commit()