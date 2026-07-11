"""create market prices table

Revision ID: 20260709_0001
Revises: 
Create Date: 2026-07-09

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260709_0001"
down_revision = "d86d3431042a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column(
            "interval",
            sa.String(length=20),
            server_default="1d",
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(length=50),
            server_default="manual",
            nullable=False,
        ),
        sa.Column("open_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("high_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("low_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("close_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("adjusted_close_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("volume", sa.Numeric(24, 4), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("exchange", sa.String(length=30), nullable=True),
        sa.Column("instrument_type", sa.String(length=30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "symbol",
            "price_date",
            "interval",
            "source",
            name="uq_market_price_symbol_date_interval_source",
        ),
    )

    op.create_index(
        op.f("ix_market_prices_id"),
        "market_prices",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_market_prices_symbol"),
        "market_prices",
        ["symbol"],
        unique=False,
    )

    op.create_index(
        op.f("ix_market_prices_price_date"),
        "market_prices",
        ["price_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_market_prices_price_date"),
        table_name="market_prices",
    )

    op.drop_index(
        op.f("ix_market_prices_symbol"),
        table_name="market_prices",
    )

    op.drop_index(
        op.f("ix_market_prices_id"),
        table_name="market_prices",
    )

    op.drop_table("market_prices")