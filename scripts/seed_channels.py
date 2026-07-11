import _bootstrap  # noqa: F401

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.channel import Channel
from app.models.source import Source


def seed_channels(db: Session):

    telegram = (
        db.query(Source)
        .filter(Source.source_name == "telegram")
        .first()
    )

    channels = [
        ("chartbankglobal", "ChartBank Global"),
        ("chartbankmv", "ChartBank MV"),
        ("chartbankcommodity", "ChartBank Commodity"),
    ]

    for channel_name, display_name in channels:

        exists = (
            db.query(Channel)
            .filter(Channel.channel_name == channel_name)
            .first()
        )

        if exists:
            continue

        db.add(
            Channel(
                source_id=telegram.id,
                channel_name=channel_name,
                display_name=display_name,
            )
        )

    db.commit()

    print("Channels seeded.")


if __name__ == "__main__":

    db = SessionLocal()

    try:
        seed_channels(db)
    finally:
        db.close()