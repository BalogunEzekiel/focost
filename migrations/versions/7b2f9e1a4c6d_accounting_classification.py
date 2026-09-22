"""Add accounting classification and links for investments and goal contributions.

Revision ID: 7b2f9e1a4c6d
Revises: 9c3e1a6d7f2b
"""
from alembic import op
import sqlalchemy as sa

revision = "7b2f9e1a4c6d"
down_revision = "9c3e1a6d7f2b"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("ai_usage", schema=None) as batch_op:
        batch_op.add_column(sa.Column("billing_period_start", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_ai_usage_billing_period_start", ["billing_period_start"], unique=False)

    with op.batch_alter_table("expenses", schema=None) as batch_op:
        batch_op.add_column(sa.Column("transaction_class", sa.String(30), nullable=True, server_default="expense"))
        batch_op.create_index("ix_expenses_transaction_class", ["transaction_class"], unique=False)

    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("source_expense_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_assets_source_expense_id", ["source_expense_id"], unique=True)
        batch_op.create_foreign_key(
            "fk_assets_source_expense", "expenses", ["source_expense_id"], ["id"], ondelete="SET NULL"
        )

    with op.batch_alter_table("goal_contributions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("expense_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_goal_contributions_expense_id", ["expense_id"], unique=True)
        batch_op.create_foreign_key(
            "fk_goal_contributions_expense", "expenses", ["expense_id"], ["id"], ondelete="SET NULL"
        )

    op.execute(
        "UPDATE expenses SET transaction_class='investment' "
        "WHERE lower(category)='investment' AND (transaction_class IS NULL OR transaction_class='expense')"
    )
    op.execute(
        "UPDATE expenses SET transaction_class='expense' WHERE transaction_class IS NULL"
    )

    # Backfill legacy investment-category cash outflows into the asset register.
    conn = op.get_bind()
    expenses = sa.table(
        "expenses",
        sa.column("id", sa.Integer),
        sa.column("user_id", sa.Integer),
        sa.column("merchant", sa.String),
        sa.column("expense_date", sa.Date),
        sa.column("amount", sa.Float),
        sa.column("notes", sa.Text),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
        sa.column("public_id", sa.String),
        sa.column("transaction_class", sa.String),
    )
    assets = sa.table(
        "assets",
        sa.column("id", sa.Integer),
        sa.column("user_id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("asset_type", sa.String),
        sa.column("investment_type", sa.String),
        sa.column("acquisition_date", sa.Date),
        sa.column("acquisition_cost", sa.Float),
        sa.column("current_value", sa.Float),
        sa.column("quantity", sa.Float),
        sa.column("cost_basis", sa.Float),
        sa.column("currency", sa.String),
        sa.column("notes", sa.Text),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
        sa.column("public_id", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("source_expense_id", sa.Integer),
    )

    legacy_investments = conn.execute(
        sa.select(expenses).where(
            expenses.c.transaction_class == "investment",
            ~sa.exists(
                sa.select(assets.c.id).where(
                    assets.c.source_expense_id == expenses.c.id
                )
            ),
        )
    ).mappings().all()

    import uuid
    for row in legacy_investments:
        conn.execute(
            assets.insert().values(
                user_id=row["user_id"],
                name=row["merchant"] or "Investment",
                asset_type="Investment",
                investment_type="Investment",
                acquisition_date=row["expense_date"],
                acquisition_cost=row["amount"],
                current_value=row["amount"],
                quantity=None,
                cost_basis=row["amount"],
                currency="NGN",
                notes=row["notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                public_id=uuid.uuid4().hex[:36],
                is_active=True,
                source_expense_id=row["id"],
            )
        )

    # Backfill legacy standalone goal contributions as internal cash transfers.
    contributions = sa.table(
        "goal_contributions",
        sa.column("id", sa.Integer),
        sa.column("user_id", sa.Integer),
        sa.column("goal_id", sa.Integer),
        sa.column("amount", sa.Float),
        sa.column("contribution_date", sa.Date),
        sa.column("note", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
        sa.column("expense_id", sa.Integer),
    )
    goals = sa.table(
        "goals",
        sa.column("id", sa.Integer),
        sa.column("title", sa.String),
    )

    legacy_contributions = conn.execute(
        sa.select(
            contributions,
            goals.c.title.label("goal_title"),
        )
        .select_from(
            contributions.join(goals, contributions.c.goal_id == goals.c.id)
        )
        .where(contributions.c.expense_id.is_(None))
    ).mappings().all()

    for row in legacy_contributions:
        result = conn.execute(
            expenses.insert().values(
                user_id=row["user_id"],
                category="Goal Contribution",
                merchant=row["goal_title"] or "Goal",
                description=f"Contribution to goal: {row['goal_title'] or row['goal_id']}",
                amount=row["amount"],
                payment_method="Internal Transfer",
                expense_date=row["contribution_date"],
                notes=row["note"],
                recurring=False,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                public_id=uuid.uuid4().hex[:36],
                transaction_class="goal_contribution",
            )
        )
        expense_id = result.inserted_primary_key[0]
        conn.execute(
            contributions.update()
            .where(contributions.c.id == row["id"])
            .values(expense_id=expense_id)
        )


def downgrade():
    with op.batch_alter_table("ai_usage", schema=None) as batch_op:
        batch_op.drop_index("ix_ai_usage_billing_period_start")
        batch_op.drop_column("billing_period_start")

    with op.batch_alter_table("goal_contributions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_goal_contributions_expense", type_="foreignkey")
        batch_op.drop_index("ix_goal_contributions_expense_id")
        batch_op.drop_column("expense_id")

    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.drop_constraint("fk_assets_source_expense", type_="foreignkey")
        batch_op.drop_index("ix_assets_source_expense_id")
        batch_op.drop_column("source_expense_id")

    with op.batch_alter_table("expenses", schema=None) as batch_op:
        batch_op.drop_index("ix_expenses_transaction_class")
        batch_op.drop_column("transaction_class")
