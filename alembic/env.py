import os
from pathlib import Path
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import pool, create_engine
from sqlalchemy.engine import URL
from alembic import context

from app.models.base import Base
from app.models.source import Source   # noqa: F401  (registers model with Base.metadata)
from app.models.channel import Channel
from app.models.message import Message  # noqa: F401  (registers model with Base.metadata)
from app.models.recommendation import Recommendation
from app.models.market_price import MarketPrice  # noqa: F401


# from app.models import Base, Source, Channel, Message, Recommendation

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)

config = context.config

# ---------------------------------------------------------------------------
# Build database URL (single source of truth)
# ---------------------------------------------------------------------------
db_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", 5432)),
    database=os.environ["POSTGRES_DB"],
)

# Alembic's config object only accepts strings, so render explicitly here.
# Everywhere else, pass the `db_url` object directly — create_engine() and
# context.configure() both accept URL objects natively, which avoids the
# password-masking issue that comes from calling str(url).
config.set_main_option("sqlalchemy.url", db_url.render_as_string(hide_password=False))

# ---------------------------------------------------------------------------
# Logging config
# ---------------------------------------------------------------------------
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without a live DB connection)."""
    context.configure(
        url=db_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects directly to the DB)."""
    connectable = create_engine(db_url, poolclass=pool.NullPool)

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