from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NormalizedMessage(Base):
    __tablename__ = "normalized_messages"

    __table_args__ = (
        UniqueConstraint(
            "message_id",
            name="uq_normalized_message"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id"),
        nullable=False
    )

    clean_text: Mapped[str | None] = mapped_column(
        Text
    )

    symbol: Mapped[str | None] = mapped_column(
        String(30)
    )

    instrument_type: Mapped[str] = mapped_column(
        String(20),
        default="UNKNOWN"
    )

    action: Mapped[str | None] = mapped_column(
        String(10)
    )

    parser_status: Mapped[str] = mapped_column(
        String(40),
        default="PENDING"
    )

    parser_version: Mapped[str] = mapped_column(
        String(20),
        default="1.0"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )