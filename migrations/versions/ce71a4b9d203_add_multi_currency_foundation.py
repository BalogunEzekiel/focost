"""Add source-currency metadata and auditable FX-rate snapshots.

Existing monetary records are explicitly backfilled as NGN without changing
any amount. The user's users.currency remains their display preference.
"""
from alembic import op
import sqlalchemy as sa

revision = "ce71a4b9d203"
down_revision = "ab31c9d8e702"
branch_labels = None
depends_on = None


LEGACY_CURRENCY_COLUMNS = (
    ("income", "currency"),
    ("expenses", "currency"),
    ("budgets", "currency"),
    ("goals", "currency"),
    ("goal_contributions", "currency"),
    ("investment_events", "currency"),
    ("users", "base_currency"),
    ("users", "monthly_income_currency"),
)


def upgrade():
    for table, column in LEGACY_CURRENCY_COLUMNS:
        with op.batch_alter_table(table) as batch:
            batch.add_column(
                sa.Column(column, sa.String(length=3), nullable=False, server_default="NGN")
            )
        # Explicit backfill documents the historical-currency assumption.
        op.execute(sa.text(f"UPDATE {table} SET {column} = 'NGN' WHERE {column} IS NULL OR {column} = ''"))

    # The user confirmed that every pre-existing investment and subscription
    # amount was denominated in NGN. Preserve every numeric amount unchanged.
    op.execute(sa.text("UPDATE assets SET currency = 'NGN'"))
    op.execute(sa.text("UPDATE subscription_plans SET currency = 'NGN'"))
    op.execute(sa.text("UPDATE payment_transactions SET currency = 'NGN'"))

    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("quote_currency", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(24, 12), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_manual", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("rate > 0", name="ck_exchange_rates_rate_positive"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("base_currency", "quote_currency", "rate_date", name="uq_exchange_rate_pair_date"),
    )
    op.create_index("ix_exchange_rates_public_id", "exchange_rates", ["public_id"], unique=True)
    op.create_index("ix_exchange_rates_base_currency", "exchange_rates", ["base_currency"])
    op.create_index("ix_exchange_rates_quote_currency", "exchange_rates", ["quote_currency"])
    op.create_index("ix_exchange_rates_rate_date", "exchange_rates", ["rate_date"])


def downgrade():
    op.drop_index("ix_exchange_rates_rate_date", table_name="exchange_rates")
    op.drop_index("ix_exchange_rates_public_id", table_name="exchange_rates")
    op.drop_index("ix_exchange_rates_quote_currency", table_name="exchange_rates")
    op.drop_index("ix_exchange_rates_base_currency", table_name="exchange_rates")
    op.drop_table("exchange_rates")
    for table, column in reversed(LEGACY_CURRENCY_COLUMNS):
        with op.batch_alter_table(table) as batch:
            batch.drop_column(column)
