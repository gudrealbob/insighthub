import _bootstrap  # noqa: F401

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.message import Message
from app.models.normalized_message import NormalizedMessage
from app.models.recommendation import Recommendation


def print_section(title):
    print("")
    print("====================================")
    print(title)
    print("====================================")


def main():
    db = SessionLocal()

    try:
        total_messages = db.query(Message).count()
        total_normalized = db.query(NormalizedMessage).count()
        total_recommendations = db.query(Recommendation).count()

        failed_normalized = (
            db.query(NormalizedMessage)
            .filter(NormalizedMessage.parser_status == "FAILED")
            .count()
        )

        missing_symbol = (
            db.query(NormalizedMessage)
            .filter(NormalizedMessage.symbol.is_(None))
            .count()
        )

        missing_action = (
            db.query(NormalizedMessage)
            .filter(NormalizedMessage.action.is_(None))
            .count()
        )

        missing_entry = (
            db.query(NormalizedMessage)
            .outerjoin(
                Recommendation,
                Recommendation.message_id == NormalizedMessage.message_id
            )
            .filter(Recommendation.id.is_(None))
            .count()
        )

        print_section("Sprint 3 Parser Quality Report")

        print(f"Total messages          : {total_messages}")
        print(f"Total normalized        : {total_normalized}")
        print(f"Total recommendations   : {total_recommendations}")
        print(f"Failed normalized       : {failed_normalized}")
        print(f"Missing symbol          : {missing_symbol}")
        print(f"Missing action          : {missing_action}")
        print(f"No recommendation row   : {missing_entry}")

        success_rate = 0

        if total_messages > 0:
            success_rate = round(
                (total_recommendations / total_messages) * 100,
                2
            )

        print(f"Recommendation rate     : {success_rate}%")

        print_section("Sample Failed / Not Recommended Messages")

        rows = (
            db.query(
                Message.id,
                NormalizedMessage.symbol,
                NormalizedMessage.action,
                NormalizedMessage.parser_status,
                NormalizedMessage.clean_text,
            )
            .join(
                NormalizedMessage,
                NormalizedMessage.message_id == Message.id
            )
            .outerjoin(
                Recommendation,
                Recommendation.message_id == Message.id
            )
            .filter(Recommendation.id.is_(None))
            .order_by(Message.id)
            .limit(25)
            .all()
        )

        for row in rows:
            print("")
            print(f"message_id     : {row.id}")
            print(f"symbol         : {row.symbol}")
            print(f"action         : {row.action}")
            print(f"parser_status  : {row.parser_status}")
            print("clean_text:")
            print(row.clean_text)

        print("")

    finally:
        db.close()


if __name__ == "__main__":
    main()