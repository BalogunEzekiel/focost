"""Finalize schema alignment with SQLAlchemy models.

Revision ID: d1e7f3a9c402
Revises: c8f1a6d3e902
"""

from alembic import op


revision = "d1e7f3a9c402"
down_revision = "c8f1a6d3e902"
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------
    # Remove indexes that are present in SQLite but are not defined
    # by the current SQLAlchemy model.
    # ------------------------------------------------------------------
    op.drop_index(
        "ix_announcements_created_at",
        table_name="announcements",
    )

    op.drop_index(
        "ix_announcements_updated_at",
        table_name="announcements",
    )

    # ------------------------------------------------------------------
    # payment_transactions
    # ------------------------------------------------------------------
    op.create_index(
        "ix_payment_transactions_plan_id",
        "payment_transactions",
        ["plan_id"],
        unique=False,
    )

    op.create_index(
        "ix_payment_transactions_provider",
        "payment_transactions",
        ["provider"],
        unique=False,
    )

    op.create_index(
        "ix_payment_transactions_subscription_id",
        "payment_transactions",
        ["subscription_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # subscription_events
    # ------------------------------------------------------------------
    op.create_index(
        "ix_subscription_events_event_type",
        "subscription_events",
        ["event_type"],
        unique=False,
    )

    op.create_index(
        "ix_subscription_events_subscription_id",
        "subscription_events",
        ["subscription_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # user_subscriptions
    # ------------------------------------------------------------------
    op.create_index(
        "ix_user_subscriptions_is_trial",
        "user_subscriptions",
        ["is_trial"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # SQLite-safe unique constraints.
    #
    # SQLite does not support ALTER TABLE ... ADD CONSTRAINT.
    # Alembic batch mode recreates the affected table while preserving
    # its data and schema.
    # ------------------------------------------------------------------
    with op.batch_alter_table(
        "paystack_customers",
        schema=None,
        recreate="always",
    ) as batch_op:
        batch_op.create_unique_constraint(
            "uq_paystack_customers_customer_code",
            ["customer_code"],
        )

    with op.batch_alter_table(
        "subscription_plans",
        schema=None,
        recreate="always",
    ) as batch_op:
        batch_op.create_unique_constraint(
            "uq_subscription_plans_paystack_plan_code",
            ["paystack_plan_code"],
        )

    with op.batch_alter_table(
        "user_subscriptions",
        schema=None,
        recreate="always",
    ) as batch_op:
        batch_op.create_unique_constraint(
            "uq_user_subscriptions_provider_subscription_code",
            ["provider_subscription_code"],
        )


def downgrade():
    with op.batch_alter_table(
        "user_subscriptions",
        schema=None,
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_user_subscriptions_provider_subscription_code",
            type_="unique",
        )

    with op.batch_alter_table(
        "subscription_plans",
        schema=None,
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_subscription_plans_paystack_plan_code",
            type_="unique",
        )

    with op.batch_alter_table(
        "paystack_customers",
        schema=None,
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_paystack_customers_customer_code",
            type_="unique",
        )

    op.drop_index(
        "ix_user_subscriptions_is_trial",
        table_name="user_subscriptions",
    )

    op.drop_index(
        "ix_subscription_events_subscription_id",
        table_name="subscription_events",
    )

    op.drop_index(
        "ix_subscription_events_event_type",
        table_name="subscription_events",
    )

    op.drop_index(
        "ix_payment_transactions_subscription_id",
        table_name="payment_transactions",
    )

    op.drop_index(
        "ix_payment_transactions_provider",
        table_name="payment_transactions",
    )

    op.drop_index(
        "ix_payment_transactions_plan_id",
        table_name="payment_transactions",
    )

    op.create_index(
        "ix_announcements_updated_at",
        "announcements",
        ["updated_at"],
        unique=False,
    )

    op.create_index(
        "ix_announcements_created_at",
        "announcements",
        ["created_at"],
        unique=False,
    )