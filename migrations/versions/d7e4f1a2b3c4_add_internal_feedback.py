"""Add internal FOCOST feedback management.

Revision ID: d7e4f1a2b3c4
Revises: c4d8e2f1a9b3
"""
from alembic import op
import sqlalchemy as sa


revision = "d7e4f1a2b3c4"
down_revision = "c4d8e2f1a9b3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("submitted_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("submitted_name", sa.String(length=160), nullable=True),
        sa.Column("submitted_email", sa.String(length=160), nullable=True),
        sa.Column(
            "category",
            sa.String(length=40),
            nullable=False,
            server_default="general",
        ),
        sa.Column("subject", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="new",
        ),
        sa.Column(
            "priority",
            sa.String(length=20),
            nullable=False,
            server_default="normal",
        ),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["submitted_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)",
            name="ck_feedback_rating_range",
        ),
    )

    op.create_index(
        "ix_feedback_submitted_by_id",
        "feedback",
        ["submitted_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_reviewed_by_id",
        "feedback",
        ["reviewed_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_submitted_email",
        "feedback",
        ["submitted_email"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_category",
        "feedback",
        ["category"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_status",
        "feedback",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_priority",
        "feedback",
        ["priority"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_status_created_at",
        "feedback",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_category_created_at",
        "feedback",
        ["category", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_feedback_priority_created_at",
        "feedback",
        ["priority", "created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_feedback_priority_created_at",
        table_name="feedback",
    )
    op.drop_index(
        "ix_feedback_category_created_at",
        table_name="feedback",
    )
    op.drop_index(
        "ix_feedback_status_created_at",
        table_name="feedback",
    )
    op.drop_index(
        "ix_feedback_priority",
        table_name="feedback",
    )
    op.drop_index(
        "ix_feedback_status",
        table_name="feedback",
    )
    op.drop_index(
        "ix_feedback_category",
        table_name="feedback",
    )
    op.drop_index(
        "ix_feedback_submitted_email",
        table_name="feedback",
    )
    op.drop_index(
        "ix_feedback_reviewed_by_id",
        table_name="feedback",
    )
    op.drop_index(
        "ix_feedback_submitted_by_id",
        table_name="feedback",
    )
    op.drop_table("feedback")
