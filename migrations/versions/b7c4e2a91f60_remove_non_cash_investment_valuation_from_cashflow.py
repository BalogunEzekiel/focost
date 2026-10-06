"""Remove non-cash investment valuation gains/losses from income and expenses.

Revision ID: b7c4e2a91f60
Revises: 3c9e7a1b5d2f
"""

from alembic import op
import sqlalchemy as sa


revision = "b7c4e2a91f60"
down_revision = "3c9e7a1b5d2f"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Valuation/revaluation is an investment carrying-value event only.
    # Older FOCOST versions incorrectly materialized these non-cash changes
    # as Income(transaction_class='investment_gain') or
    # Expense(transaction_class='investment_loss').
    #
    # Clear the event links first so the cleanup is safe even when the
    # database does not have foreign-key enforcement enabled.
    conn.execute(
        sa.text(
            """
            UPDATE investment_events
            SET income_id = NULL
            WHERE event_type = 'valuation'
              AND income_id IS NOT NULL
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE investment_events
            SET expense_id = NULL
            WHERE event_type = 'valuation'
              AND expense_id IS NOT NULL
            """
        )
    )

    # Remove all legacy valuation accounting rows. These transaction classes
    # were created only by the old investment valuation implementation.
    conn.execute(
        sa.text(
            """
            DELETE FROM income
            WHERE transaction_class = 'investment_gain'
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM expenses
            WHERE transaction_class = 'investment_loss'
            """
        )
    )


def downgrade():
    # Recreate the old accounting rows from valuation events so the migration
    # remains reversible. These rows are intentionally restored only when a
    # developer explicitly downgrades to the old accounting model.
    conn = op.get_bind()

    income_table = sa.table(
        "income",
        sa.column("id", sa.Integer),
        sa.column("public_id", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
        sa.column("is_active", sa.Boolean),
        sa.column("user_id", sa.Integer),
        sa.column("source", sa.String),
        sa.column("category", sa.String),
        sa.column("amount", sa.Float),
        sa.column("received_date", sa.Date),
        sa.column("notes", sa.Text),
        sa.column("recurring", sa.Boolean),
        sa.column("transaction_class", sa.String),
    )

    expense_table = sa.table(
        "expenses",
        sa.column("id", sa.Integer),
        sa.column("public_id", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
        sa.column("is_active", sa.Boolean),
        sa.column("user_id", sa.Integer),
        sa.column("category", sa.String),
        sa.column("merchant", sa.String),
        sa.column("description", sa.String),
        sa.column("amount", sa.Float),
        sa.column("payment_method", sa.String),
        sa.column("expense_date", sa.Date),
        sa.column("notes", sa.Text),
        sa.column("recurring", sa.Boolean),
        sa.column("transaction_class", sa.String),
    )

    events = sa.table(
        "investment_events",
        sa.column("id", sa.Integer),
        sa.column("public_id", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
        sa.column("is_active", sa.Boolean),
        sa.column("asset_id", sa.Integer),
        sa.column("user_id", sa.Integer),
        sa.column("event_type", sa.String),
        sa.column("event_date", sa.Date),
        sa.column("amount", sa.Float),
        sa.column("realized_gain_loss", sa.Float),
        sa.column("notes", sa.Text),
        sa.column("income_id", sa.Integer),
        sa.column("expense_id", sa.Integer),
    )

    assets = sa.table(
        "assets",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
    )

    import uuid
    from datetime import datetime

    rows = conn.execute(
        sa.select(
            events,
            assets.c.name.label("asset_name"),
        )
        .select_from(
            events.join(assets, events.c.asset_id == assets.c.id)
        )
        .where(events.c.event_type == "valuation")
        .order_by(events.c.id.asc())
    ).mappings().all()

    for row in rows:
        gain_loss = float(row["realized_gain_loss"] or 0)
        if abs(gain_loss) < 1e-12:
            continue

        now = datetime.utcnow()

        if gain_loss > 0:
            result = conn.execute(
                income_table.insert().values(
                    public_id=str(uuid.uuid4()),
                    created_at=row["created_at"] or now,
                    updated_at=row["updated_at"] or now,
                    is_active=True,
                    user_id=row["user_id"],
                    source=row["asset_name"] or "Investment",
                    category="Investment Gain",
                    amount=gain_loss,
                    received_date=row["event_date"],
                    notes=row["notes"] or "Investment valuation gain.",
                    recurring=False,
                    transaction_class="investment_gain",
                )
            )
            income_id = result.inserted_primary_key[0]
            conn.execute(
                events.update()
                .where(events.c.id == row["id"])
                .values(income_id=income_id)
            )
        else:
            loss = abs(gain_loss)
            result = conn.execute(
                expense_table.insert().values(
                    public_id=str(uuid.uuid4()),
                    created_at=row["created_at"] or now,
                    updated_at=row["updated_at"] or now,
                    is_active=True,
                    user_id=row["user_id"],
                    category="Investment Loss",
                    merchant=(row["asset_name"] or "Investment")[:150],
                    description="Investment valuation loss",
                    amount=loss,
                    payment_method="Investment Valuation",
                    expense_date=row["event_date"],
                    notes=row["notes"] or "Investment valuation loss.",
                    recurring=False,
                    transaction_class="investment_loss",
                )
            )
            expense_id = result.inserted_primary_key[0]
            conn.execute(
                events.update()
                .where(events.c.id == row["id"])
                .values(expense_id=expense_id)
            )