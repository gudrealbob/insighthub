from sqlalchemy.orm import Session

from app.models.source import Source


def get_source_by_name(db: Session, source_name: str) -> Source:
    return (
        db.query(Source)
        .filter(Source.source_name == source_name)
        .first()
    )