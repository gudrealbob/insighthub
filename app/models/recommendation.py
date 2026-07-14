from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from app.models.base import Base


class Recommendation(Base):

    __tablename__ = "recommendations"

    __table_args__ = (
        UniqueConstraint(
            "message_id",
            name="uq_recommendation_message",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    message_id = Column(
        Integer,
        ForeignKey("messages.id"),
        nullable=False,
    )

    symbol = Column(
        String(60),
        nullable=False,
    )

    action = Column(
        String(10),
        nullable=False,
    )

    entry_low = Column(Numeric)
    entry_high = Column(Numeric)

    entry_instruction = Column(
        String(30),
        nullable=False,
        default="UNSPECIFIED",
        server_default="UNSPECIFIED",
    )

    entry_instruction_text = Column(Text)

    entry_price_source = Column(
        String(30),
        nullable=False,
        default="MESSAGE",
        server_default="MESSAGE",
    )

    entry_price_timestamp = Column(
        DateTime(timezone=True)
    )

    stop_loss = Column(Numeric)

    support_level = Column(Numeric)

    trigger_level = Column(Numeric)

    target1 = Column(Numeric)
    target2 = Column(Numeric)
    target3 = Column(Numeric)

    targets_json = Column(JSON)

    pattern = Column(String(100))

    risk = Column(String(30))