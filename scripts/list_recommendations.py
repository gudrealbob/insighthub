import _bootstrap  # noqa: F401

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.recommendation_query_service import get_all_recommendations


db = SessionLocal()

try:
    recommendations = get_all_recommendations(db)

    print(f"\nFound {len(recommendations)} recommendation(s)\n")

    for r in recommendations:
        print("-" * 60)
        print(f"ID : {r.id}")
        print(f"Symbol : {r.symbol}")
        print(f"Action : {r.action}")
        print(f"Entry : {r.entry_low} - {r.entry_high}")
        print(f"SL : {r.stop_loss}")
        print(f"Target 1 : {r.target1}")
        print(f"Target 2 : {r.target2}")
        print(f"Target 3 : {r.target3}")

finally:
    db.close()