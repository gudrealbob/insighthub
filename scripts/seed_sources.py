from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.source import Source


def seed_sources(db: Session):
    source = (
        db.query(Source)
        .filter(Source.source_name == "telegram")
        .first()
    )

    if source:
        print(f"Source already exists (id={source.id})")
        return source

    source = Source(
        source_type="TELEGRAM",
        source_name="telegram",
        display_name="Telegram",
        is_active=True,
    )

    db.add(source)
    db.commit()
    db.refresh(source)

    print(f"Created Source (id={source.id})")

    return source


if __name__ == "__main__":
    db = SessionLocal()

    try:
        seed_sources(db)
    finally:
        db.close()