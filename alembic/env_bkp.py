from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from alembic import context

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.engine import URL

from app.models.base import Base
from app.models.source import Source
from app.models.message import Message
from urllib.parse import quote_plus
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

# Load .env

load_dotenv(dotenv_path=ENV_PATH, override=True)
print("Loaded .env from:", ENV_PATH)
print("CWD:", os.getcwd())
print("ENV PASSWORD:", os.getenv("POSTGRES_PASSWORD"))
print("ENV PASSWORD REPR:", repr(os.getenv("POSTGRES_PASSWORD")))
print("ENV USER:", os.getenv("POSTGRES_USER"))
config = context.config

# quoted_password = quote_plus(os.getenv("POSTGRES_PASSWORD"))
# print("Quoted password:", quoted_password)

# Build DB URL (single source of truth)

#url = URL.create(
#    drivername="postgresql+psycopg",
#    username=os.getenv("POSTGRES_USER"),
#    password="K3nhaa2k264HL",
#    host=os.getenv("POSTGRES_HOST", "localhost"),
#    port=int(os.getenv("POSTGRES_PORT", 5432)),
#    database=os.getenv("POSTGRES_DB"),
#)

print("ENV USER REPR:", repr(os.getenv("POSTGRES_USER")))
print("ENV HOST REPR:", repr(os.getenv("POSTGRES_HOST")))
print("ENV PORT REPR:", repr(os.getenv("POSTGRES_PORT")))
print("ENV DB REPR:", repr(os.getenv("POSTGRES_DB")))

url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("POSTGRES_USER"),
    password="K3nhaa2k264HL",
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", 5432)),
    database=os.getenv("POSTGRES_DB"),
)

# Force-print the REAL connection string, password included, no masking
print("REAL DB URL:", url.render_as_string(hide_password=False))

print("DB URL:", url)
print("DB URL REPR:", repr(url))
# Logging config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    ...


def run_migrations_online():

    db_url = url.render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", db_url)
    connectable = create_engine(
        db_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()