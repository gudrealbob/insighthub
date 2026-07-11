from __future__ import annotations

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)

from app.models.base import Base


class Recommendation(Base):

    __tablename__ = "recommendations"

    __table_args__ = (
        UniqueConstraint(
            "message_id",
            name="uq_recommendation_message"
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    message_id = Column(
        Integer,
        ForeignKey("messages.id"),
        nullable=False
    )

    symbol = Column(String(30))
    action = Column(String(10))

    entry_low = Column(Numeric)
    entry_high = Column(Numeric)

    stop_loss = Column(Numeric)

    target1 = Column(Numeric)
    target2 = Column(Numeric)
    target3 = Column(Numeric)

    targets_json = Column(JSON)

    pattern = Column(String(100))
    risk = Column(String(30))