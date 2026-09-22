"""Add production billing, AI usage, webhook, and asset domains.

Revision ID: 8f4d2a7c1b9e
Revises: 45a8ac647194
"""
from alembic import op
import sqlalchemy as sa
import json

revision = "8f4d2a7c1b9e"
down_revision = "45a8ac647194"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("subscription_plans",
        sa.Column("slug", sa.String(60), nullable=False), sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text()), sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="NGN"),
        sa.Column("interval", sa.String(20), nullable=False, server_default="monthly"),
        sa.Column("ai_token_limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ai_request_limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transaction_limit", sa.Integer()), sa.Column("feature_entitlements", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("paystack_plan_code", sa.String(120)), sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"), sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("public_id", sa.String(36), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("slug"), sa.UniqueConstraint("paystack_plan_code"))
    op.create_index("ix_subscription_plans_slug", "subscription_plans", ["slug"], unique=True)

    op.create_table("user_subscriptions",
        sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("plan_id", sa.Integer()), sa.Column("status", sa.String(30), nullable=False, server_default="trial"),
        sa.Column("is_trial", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("trial_started_at", sa.DateTime()), sa.Column("trial_ends_at", sa.DateTime()),
        sa.Column("started_at", sa.DateTime()), sa.Column("current_period_start", sa.DateTime()), sa.Column("current_period_end", sa.DateTime()),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("canceled_at", sa.DateTime()),
        sa.Column("provider", sa.String(30), nullable=False, server_default="paystack"), sa.Column("provider_subscription_code", sa.String(160)),
        sa.Column("provider_email_token", sa.String(255)), sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("public_id", sa.String(36), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("provider_subscription_code"))
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"])
    op.create_index("ix_user_subscriptions_plan_id", "user_subscriptions", ["plan_id"])
    op.create_index("ix_user_subscriptions_status", "user_subscriptions", ["status"])

    op.create_table("payment_transactions",
        sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("plan_id", sa.Integer()), sa.Column("subscription_id", sa.Integer()),
        sa.Column("provider", sa.String(30), nullable=False, server_default="paystack"), sa.Column("reference", sa.String(160), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False), sa.Column("currency", sa.String(10), nullable=False, server_default="NGN"),
        sa.Column("status", sa.String(30), nullable=False, server_default="initialized"), sa.Column("gateway_response", sa.Text()), sa.Column("paid_at", sa.DateTime()),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"), sa.Column("id", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("public_id", sa.String(36), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]), sa.ForeignKeyConstraint(["subscription_id"], ["user_subscriptions.id"]), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("reference"))
    op.create_index("ix_payment_transactions_reference", "payment_transactions", ["reference"], unique=True)
    op.create_index("ix_payment_transactions_user_id", "payment_transactions", ["user_id"])
    op.create_index("ix_payment_transactions_status", "payment_transactions", ["status"])

    op.create_table("payment_attempts",
        sa.Column("transaction_id", sa.Integer(), nullable=False), sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"), sa.Column("action", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False), sa.Column("response_code", sa.String(20)), sa.Column("response_message", sa.Text()), sa.Column("duration_ms", sa.Integer()),
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("public_id", sa.String(36), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["transaction_id"], ["payment_transactions.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_payment_attempts_transaction_id", "payment_attempts", ["transaction_id"])

    op.create_table("paystack_customers",
        sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("customer_code", sa.String(160), nullable=False), sa.Column("provider_email", sa.String(160), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("public_id", sa.String(36), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("user_id"), sa.UniqueConstraint("customer_code"))

    op.create_table("payment_webhook_events",
        sa.Column("provider", sa.String(30), nullable=False, server_default="paystack"), sa.Column("event_key", sa.String(255), nullable=False), sa.Column("event_type", sa.String(100), nullable=False), sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("signature", sa.String(255)), sa.Column("status", sa.String(30), nullable=False, server_default="received"), sa.Column("processed_at", sa.DateTime()), sa.Column("error_message", sa.Text()),
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("public_id", sa.String(36), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("event_key"))
    op.create_index("ix_payment_webhook_events_event_key", "payment_webhook_events", ["event_key"], unique=True)
    op.create_index("ix_payment_webhook_events_event_type", "payment_webhook_events", ["event_type"])

    op.create_table("subscription_events",
        sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("subscription_id", sa.Integer()), sa.Column("event_type", sa.String(80), nullable=False), sa.Column("old_status", sa.String(30)), sa.Column("new_status", sa.String(30)), sa.Column("source", sa.String(40), nullable=False, server_default="system"), sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("public_id", sa.String(36), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["subscription_id"], ["user_subscriptions.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_subscription_events_user_id", "subscription_events", ["user_id"])

    op.create_table("ai_usage",
        sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("request_id", sa.String(80), nullable=False), sa.Column("provider", sa.String(80)), sa.Column("model", sa.String(160)),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"), sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"), sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"), sa.Column("duration_ms", sa.Integer()), sa.Column("estimated_cost_minor", sa.Integer(), nullable=False, server_default="0"), sa.Column("status", sa.String(30), nullable=False, server_default="success"), sa.Column("error_message", sa.Text()),
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("public_id", sa.String(36), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("request_id"))
    op.create_index("ix_ai_usage_user_id", "ai_usage", ["user_id"])
    op.create_index("ix_ai_usage_request_id", "ai_usage", ["request_id"], unique=True)
    op.create_index("ix_ai_usage_status", "ai_usage", ["status"])

    op.create_table("assets",
        sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("asset_type", sa.String(80), nullable=False), sa.Column("investment_type", sa.String(100)), sa.Column("acquisition_date", sa.Date()), sa.Column("acquisition_cost", sa.Float(), nullable=False, server_default="0"), sa.Column("current_value", sa.Float(), nullable=False, server_default="0"), sa.Column("quantity", sa.Float()), sa.Column("cost_basis", sa.Float()), sa.Column("currency", sa.String(10), nullable=False, server_default="NGN"), sa.Column("notes", sa.Text()),
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("public_id", sa.String(36), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_assets_user_id", "assets", ["user_id"])
    op.create_index("ix_assets_asset_type", "assets", ["asset_type"])

    plans = [
        ("essential", "Essential", "Core financial coaching for everyday money management.", 490000, 50000, 200, None, 1, {"ai_chat": True, "forecasting": True, "insights": True, "advanced_forecasting": False, "scenario_analysis": False, "asset_analytics": False}),
        ("plus", "Plus", "Deeper analytics, forecasting and personalized coaching.", 990000, 150000, 600, 5000, 2, {"ai_chat": True, "forecasting": True, "insights": True, "advanced_forecasting": True, "scenario_analysis": True, "asset_analytics": True}),
        ("pro", "Pro", "Full FOCOST intelligence for advanced personal finance management.", 1490000, 400000, 1500, 20000, 3, {"ai_chat": True, "forecasting": True, "insights": True, "advanced_forecasting": True, "scenario_analysis": True, "asset_analytics": True, "priority_ai": True}),
    ]
    for slug, name, desc, amount, tokens, requests, tx_limit, order, features in plans:
        op.execute(
            sa.text(
                "INSERT INTO subscription_plans "
                "(slug,name,description,amount_minor,currency,interval,"
                "ai_token_limit,ai_request_limit,transaction_limit,"
                "feature_entitlements,paystack_plan_code,is_public,sort_order,"
                "created_at,updated_at,public_id,is_active) "
                "VALUES (:slug,:name,:desc,:amount,'NGN','monthly',"
                ":tokens,:requests,:tx,:features,NULL,1,:order,"
                "CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,:public_id,1)"
            ).bindparams(
                slug=slug,
                name=name,
                desc=desc,
                amount=amount,
                tokens=tokens,
                requests=requests,
                tx=tx_limit,
                features=json.dumps(features),
                order=order,
                public_id=__import__("uuid").uuid4().hex[:36],
            )
        )

def downgrade():
    for table in ["assets", "ai_usage", "subscription_events", "payment_webhook_events", "paystack_customers", "payment_attempts", "payment_transactions", "user_subscriptions", "subscription_plans"]:
        op.drop_table(table)
