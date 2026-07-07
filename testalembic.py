from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from sqlalchemy import text


url = URL.create(
    drivername="postgresql+psycopg",
    username="homelab_admin",
    password="K3nhaa2k264HL",
    host="localhost",
    port=5432,
    database="ihub",
)

engine = create_engine(url)

with engine.connect() as conn:
    print(conn.execute(text("SELECT current_user")).fetchone())