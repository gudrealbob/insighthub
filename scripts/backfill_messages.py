import _bootstrap  # noqa: F401

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.message import Message
from app.services.normalization_service import normalize_message
from app.services.recommendation_service import save_recommendation


def main():
    db = SessionLocal()

    processed = 0
    recommendations_created_or_existing = 0
    failed = 0

    try:
        messages = (
            db.query(Message)
            .order_by(Message.id)
            .all()
        )

        print("")
        print("====================================")
        print("Sprint 3 Backfill Started")
        print("====================================")
        print(f"Messages found: {len(messages)}")
        print("====================================")
        print("")

        for message in messages:
            try:
                normalize_message(db, message)

                recommendation = save_recommendation(db, message)

                if recommendation is not None:
                    recommendations_created_or_existing += 1

                processed += 1

                if processed % 100 == 0:
                    print(f"Processed {processed} messages...")

            except Exception as ex:
                db.rollback()
                failed += 1

                print(
                    f"FAILED message_id={message.id}: {ex}"
                )

        print("")
        print("====================================")
        print("Sprint 3 Backfill Complete")
        print("====================================")
        print(f"Processed messages       : {processed}")
        print(f"Recommendation rows found: {recommendations_created_or_existing}")
        print(f"Failed messages          : {failed}")
        print("====================================")
        print("")

    finally:
        db.close()


if __name__ == "__main__":
    main()