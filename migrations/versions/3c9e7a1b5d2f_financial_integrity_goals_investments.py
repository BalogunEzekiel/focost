"""Add financial integrity and investment event tracking.

Revision ID: 3c9e7a1b5d2f
Revises: 245da8eb0855
"""
from alembic import op
import sqlalchemy as sa

revision = "3c9e7a1b5d2f"
down_revision = "245da8eb0855"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("income", schema=None) as batch_op:
        batch_op.add_column(sa.Column("transaction_class", sa.String(30), nullable=True, server_default="income"))
        batch_op.create_index("ix_income_transaction_class", ["transaction_class"], unique=False)

    with op.batch_alter_table("income", schema=None) as batch_op:
        batch_op.alter_column("transaction_class", server_default=None)

    op.create_table(
        "investment_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("previous_value", sa.Float(), nullable=True),
        sa.Column("new_value", sa.Float(), nullable=True),
        sa.Column("cost_basis_change", sa.Float(), nullable=False, server_default="0"),
        sa.Column("realized_gain_loss", sa.Float(), nullable=False, server_default="0"),
        sa.Column("proceeds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("expense_id", sa.Integer(), nullable=True),
        sa.Column("income_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["expense_id"], ["expenses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["income_id"], ["income.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("expense_id"),
        sa.UniqueConstraint("income_id"),
        sa.CheckConstraint("amount >= 0", name="ck_investment_event_amount_nonnegative"),
    )
    op.create_index("ix_investment_events_asset_id", "investment_events", ["asset_id"], unique=False)
    op.create_index("ix_investment_events_user_id", "investment_events", ["user_id"], unique=False)
    op.create_index("ix_investment_events_event_type", "investment_events", ["event_type"], unique=False)
    op.create_index("ix_investment_events_event_date", "investment_events", ["event_date"], unique=False)

    # Positive/non-negative integrity constraints. Cross-row goal caps and cash
    # sufficiency remain application-level rules because they depend on aggregates.
    with op.batch_alter_table("goals", schema=None) as batch_op:
        batch_op.create_check_constraint("ck_goals_target_amount_positive", "target_amount > 0")
    with op.batch_alter_table("goal_contributions", schema=None) as batch_op:
        batch_op.create_check_constraint("ck_goal_contributions_amount_positive", "amount > 0")
    with op.batch_alter_table("expenses", schema=None) as batch_op:
        batch_op.create_check_constraint("ck_expenses_amount_positive", "amount > 0")
    with op.batch_alter_table("income", schema=None) as batch_op:
        batch_op.create_check_constraint("ck_income_amount_positive", "amount > 0")
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.create_check_constraint("ck_assets_current_value_nonnegative", "current_value >= 0")
        batch_op.create_check_constraint("ck_assets_acquisition_cost_nonnegative", "acquisition_cost >= 0")
        batch_op.create_check_constraint("ck_assets_cost_basis_nonnegative", "cost_basis IS NULL OR cost_basis >= 0")


def downgrade():
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.drop_constraint("ck_assets_cost_basis_nonnegative", type_="check")
        batch_op.drop_constraint("ck_assets_acquisition_cost_nonnegative", type_="check")
        batch_op.drop_constraint("ck_assets_current_value_nonnegative", type_="check")
    with op.batch_alter_table("income", schema=None) as batch_op:
        batch_op.drop_constraint("ck_income_amount_positive", type_="check")
    with op.batch_alter_table("expenses", schema=None) as batch_op:
        batch_op.drop_constraint("ck_expenses_amount_positive", type_="check")
    with op.batch_alter_table("goal_contributions", schema=None) as batch_op:
        batch_op.drop_constraint("ck_goal_contributions_amount_positive", type_="check")
    with op.batch_alter_table("goals", schema=None) as batch_op:
        batch_op.drop_constraint("ck_goals_target_amount_positive", type_="check")

    op.drop_index("ix_investment_events_event_date", table_name="investment_events")
    op.drop_index("ix_investment_events_event_type", table_name="investment_events")
    op.drop_index("ix_investment_events_user_id", table_name="investment_events")
    op.drop_index("ix_investment_events_asset_id", table_name="investment_events")
    op.drop_table("investment_events")

    with op.batch_alter_table("income", schema=None) as batch_op:
        batch_op.drop_index("ix_income_transaction_class")
        batch_op.drop_column("transaction_class")
