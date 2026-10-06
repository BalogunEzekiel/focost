"""Add financial category registry, analytics and communications.

Revision ID: e2a7c4f9b601
Revises: d7e4f1a2b3c4
"""
from alembic import op
import sqlalchemy as sa

revision = "e2a7c4f9b601"
down_revision = "d7e4f1a2b3c4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("category_type", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "category_type", "name", name="uq_financial_category_owner_type_name"),
        sa.CheckConstraint("category_type IN ('income', 'expense')", name="ck_financial_category_type"),
    )
    op.create_index("ix_financial_categories_user_id", "financial_categories", ["user_id"])
    op.create_index("ix_financial_category_type_active", "financial_categories", ["category_type", "is_active"])

    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("announcement_type", sa.String(length=30), nullable=False, server_default="notice"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("audience", sa.String(length=30), nullable=False, server_default="all"),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("in_app", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("dashboard_banner", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("flyer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("email", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("push", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("action_url", sa.String(length=500), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("published_by_id", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["published_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_announcements_status", "announcements", ["status"])
    op.create_index("ix_announcements_audience", "announcements", ["audience"])
    op.create_index("ix_announcements_starts_at", "announcements", ["starts_at"])
    op.create_index("ix_announcements_ends_at", "announcements", ["ends_at"])

    # Backward-compatible registry migration: seed system categories here so
    # existing deployments get the same authoritative choices immediately.
    bind = op.get_bind()
    categories = {
        "income": ("Salary", "Business", "Freelance", "Investment", "Rental Income", "Commission", "Ride Business", "Gift", "Bonus", "Dividend", "Other"),
        "expense": ("Food", "Transportation", "Housing", "Telephone", "Utilities", "Gas", "Healthcare", "Education", "Entertainment", "Support/Assistance", "Shopping", "Petrol", "Petrol Contribution", "Insurance", "Travel", "Rent", "Repairs", "Family", "Toiletries", "Clothing", "Personal Care", "Tax", "Gift", "Salary", "Business", "Other"),
    }
    for kind, names in categories.items():
        for name in names:
            bind.execute(sa.text(
                "INSERT INTO financial_categories "
                "(public_id, created_at, updated_at, is_active, user_id, category_type, name, is_system) "
                "VALUES (:pid, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, NULL, :kind, :name, 1)"
            ), {"pid": __import__("uuid").uuid4().hex, "kind": kind, "name": name})


def downgrade():
    op.drop_index("ix_announcements_ends_at", table_name="announcements")
    op.drop_index("ix_announcements_starts_at", table_name="announcements")
    op.drop_index("ix_announcements_audience", table_name="announcements")
    op.drop_index("ix_announcements_status", table_name="announcements")
    op.drop_table("announcements")
    op.drop_index("ix_financial_category_type_active", table_name="financial_categories")
    op.drop_index("ix_financial_categories_user_id", table_name="financial_categories")
    op.drop_table("financial_categories")
