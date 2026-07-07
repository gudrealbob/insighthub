from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from app.models.base import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)

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
    pattern = Column(String(100))
    risk = Column(String(30))