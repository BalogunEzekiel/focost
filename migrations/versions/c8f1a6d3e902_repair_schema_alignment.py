"""Repair schema alignment after SQLite batch migrations.

Revision ID: c8f1a6d3e902
Revises: b7d3e1f4a902
"""

from alembic import op
import sqlalchemy as sa


revision = "c8f1a6d3e902"
down_revision = "b7d3e1f4a902"
branch_labels = None
depends_on = None


def _index_names(bind, table_name):
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _foreign_keys(bind, table_name):
    inspector = sa.inspect(bind)
    return inspector.get_foreign_keys(table_name)


def _has_foreign_key(bind, table_name, local_column, referred_table, referred_column):
    for fk in _foreign_keys(bind, table_name):
        if (
            fk.get("referred_table") == referred_table
            and fk.get("constrained_columns") == [local_column]
            and fk.get("referred_columns") == [referred_column]
        ):
            return True
    return False


def _create_indexes(bind, table_name, indexes):
    existing = _index_names(bind, table_name)

    for index_name, columns, unique in indexes:
        if index_name not in existing:
            op.create_index(
                index_name,
                table_name,
                columns,
                unique=unique,
            )


def _make_not_null(table_name, column_name, existing_type):
    with op.batch_alter_table(
        table_name,
        schema=None,
        recreate="always",
    ) as batch_op:
        batch_op.alter_column(
            column_name,
            existing_type=existing_type,
            nullable=False,
        )


def upgrade():
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Restore missing foreign keys.
    #
    # Existing data was already verified before this migration:
    # assets.source_expense_id -> expenses.id
    # goal_contributions.expense_id -> expenses.id
    #
    # Both relationships contain valid references and no duplicates.
    # ------------------------------------------------------------------

    if not _has_foreign_key(
        bind,
        "assets",
        "source_expense_id",
        "expenses",
        "id",
    ):
        with op.batch_alter_table(
            "assets",
            schema=None,
            recreate="always",
        ) as batch_op:
            batch_op.create_foreign_key(
                "fk_assets_source_expense",
                "expenses",
                ["source_expense_id"],
                ["id"],
                ondelete="SET NULL",
            )

    bind = op.get_bind()

    if not _has_foreign_key(
        bind,
        "goal_contributions",
        "expense_id",
        "expenses",
        "id",
    ):
        with op.batch_alter_table(
            "goal_contributions",
            schema=None,
            recreate="always",
        ) as batch_op:
            batch_op.create_foreign_key(
                "fk_goal_contributions_expense",
                "expenses",
                ["expense_id"],
                ["id"],
                ondelete="SET NULL",
            )

    # ------------------------------------------------------------------
    # 2. Restore missing explicit indexes.
    #
    # Existing UNIQUE constraints / SQLite autoindexes are intentionally
    # preserved. We only add indexes that the current schema expects and
    # that are physically absent.
    # ------------------------------------------------------------------

    bind = op.get_bind()

    indexes = {
        "ai_usage": [
            ("ix_ai_usage_public_id", ["public_id"], True),
            ("ix_ai_usage_request_id", ["request_id"], True),
            ("ix_ai_usage_status", ["status"], False),
            ("ix_ai_usage_user_id", ["user_id"], False),
        ],
        "announcements": [
            ("ix_announcements_public_id", ["public_id"], True),
            ("ix_announcements_announcement_type", ["announcement_type"], False),
            ("ix_announcements_created_at", ["created_at"], False),
            ("ix_announcements_updated_at", ["updated_at"], False),
        ],
        "assets": [
            ("ix_assets_public_id", ["public_id"], True),
            ("ix_assets_user_id", ["user_id"], False),
            ("ix_assets_asset_type", ["asset_type"], False),
        ],
        "auth_throttles": [
            ("ix_auth_throttles_public_id", ["public_id"], True),
        ],
        "auth_tokens": [
            ("ix_auth_tokens_public_id", ["public_id"], True),
        ],
        "document_archive": [
            ("ix_document_archive_public_id", ["public_id"], True),
        ],
        "feedback": [
            ("ix_feedback_public_id", ["public_id"], True),
        ],
        "financial_categories": [
            ("ix_financial_categories_public_id", ["public_id"], True),
            ("ix_financial_categories_category_type", ["category_type"], False),
        ],
        "investment_events": [
            ("ix_investment_events_public_id", ["public_id"], True),
        ],
        "payment_attempts": [
            ("ix_payment_attempts_public_id", ["public_id"], True),
            ("ix_payment_attempts_transaction_id", ["transaction_id"], False),
        ],
        "payment_transactions": [
            ("ix_payment_transactions_public_id", ["public_id"], True),
            ("ix_payment_transactions_reference", ["reference"], True),
            ("ix_payment_transactions_user_id", ["user_id"], False),
            ("ix_payment_transactions_status", ["status"], False),
        ],
        "payment_webhook_events": [
            ("ix_payment_webhook_events_public_id", ["public_id"], True),
            ("ix_payment_webhook_events_event_key", ["event_key"], True),
            ("ix_payment_webhook_events_event_type", ["event_type"], False),
        ],
        "paystack_customers": [
            ("ix_paystack_customers_public_id", ["public_id"], True),
        ],
        "policy_acceptances": [
            ("ix_policy_acceptances_public_id", ["public_id"], True),
        ],
        "policy_documents": [
            ("ix_policy_documents_public_id", ["public_id"], True),
        ],
        "push_devices": [
            ("ix_push_devices_public_id", ["public_id"], True),
        ],
        "subscription_events": [
            ("ix_subscription_events_public_id", ["public_id"], True),
            ("ix_subscription_events_user_id", ["user_id"], False),
        ],
        "subscription_plans": [
            ("ix_subscription_plans_public_id", ["public_id"], True),
            ("ix_subscription_plans_slug", ["slug"], True),
        ],
        "user_subscriptions": [
            ("ix_user_subscriptions_public_id", ["public_id"], True),
            ("ix_user_subscriptions_user_id", ["user_id"], False),
            ("ix_user_subscriptions_plan_id", ["plan_id"], False),
            ("ix_user_subscriptions_status", ["status"], False),
        ],
    }

    for table_name, table_indexes in indexes.items():
        _create_indexes(bind, table_name, table_indexes)

    # ------------------------------------------------------------------
    # 3. Correct push_devices.token explicit index.
    #
    # The table already has a UNIQUE constraint on token, but the
    # explicit model index is also declared unique=True.
    #
    # The table was verified to contain zero rows before this migration.
    # ------------------------------------------------------------------

    bind = op.get_bind()
    existing_push_indexes = _index_names(bind, "push_devices")

    if "ix_push_devices_token" in existing_push_indexes:
        op.drop_index(
            "ix_push_devices_token",
            table_name="push_devices",
        )

    op.create_index(
        "ix_push_devices_token",
        "push_devices",
        ["token"],
        unique=True,
    )

    # ------------------------------------------------------------------
    # 4. Align required NOT NULL columns.
    #
    # The database was audited before this migration and none of these
    # columns currently contains NULL values.
    #
    # SQLite-safe batch recreation is used.
    # ------------------------------------------------------------------

    not_null_columns = [
        ("ai_usage", "id", sa.Integer()),
        ("announcements", "created_at", sa.DateTime()),
        ("announcements", "updated_at", sa.DateTime()),
        ("assets", "id", sa.Integer()),
        ("expenses", "transaction_class", sa.String(length=30)),
        ("financial_categories", "created_at", sa.DateTime()),
        ("financial_categories", "updated_at", sa.DateTime()),
        ("income", "transaction_class", sa.String(length=30)),
        ("payment_attempts", "id", sa.Integer()),
        ("payment_transactions", "id", sa.Integer()),
        ("payment_webhook_events", "id", sa.Integer()),
        ("paystack_customers", "id", sa.Integer()),
        ("push_devices", "created_at", sa.DateTime()),
        ("push_devices", "updated_at", sa.DateTime()),
        ("subscription_events", "id", sa.Integer()),
        ("subscription_plans", "id", sa.Integer()),
        ("user_subscriptions", "id", sa.Integer()),
    ]

    for table_name, column_name, column_type in not_null_columns:
        _make_not_null(
            table_name,
            column_name,
            column_type,
        )


def downgrade():
    # This repair migration is intentionally conservative.
    #
    # Reversing it automatically could remove indexes/constraints that
    # existed independently of this repair and could therefore weaken
    # the schema unexpectedly.
    #
    # The migration remains reversible at the Alembic revision level,
    # but no destructive downgrade operations are performed here.
    pass