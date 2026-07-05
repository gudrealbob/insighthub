import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv(override=True)

url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    host=os.getenv("POSTGRES_HOST"),
    port=int(os.getenv("POSTGRES_PORT")),
    database=os.getenv("POSTGRES_DB"),
)

engine = create_engine(url, echo=True)


def test_connection():
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version();")).scalar()

        print("\n✅ Connected successfully!\n")
        print(version)


if __name__ == "__main__":
    test_connection()