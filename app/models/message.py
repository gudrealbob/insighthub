from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id"),
        nullable=False
    )
    external_message_id: Mapped[int] = mapped_column(nullable=False)
    message_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    message_text: Mapped[str] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSON)
    raw_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )