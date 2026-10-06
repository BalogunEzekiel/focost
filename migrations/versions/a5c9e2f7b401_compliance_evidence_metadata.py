"""Add immutable policy evidence metadata.

Revision ID: a5c9e2f7b401
Revises: f4b2c8d9e701
"""

from alembic import op
import sqlalchemy as sa


revision = "a5c9e2f7b401"
down_revision = "f4b2c8d9e701"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # policy_documents
    # ------------------------------------------------------------------
    inspector = sa.inspect(bind)

    policy_document_columns = {
        column["name"]
        for column in inspector.get_columns("policy_documents")
    }

    if "content_hash" not in policy_document_columns:
        op.add_column(
            "policy_documents",
            sa.Column(
                "content_hash",
                sa.String(length=64),
                nullable=True,
            ),
        )

    inspector = sa.inspect(bind)

    policy_document_indexes = {
        index["name"]
        for index in inspector.get_indexes("policy_documents")
    }

    if "ix_policy_documents_content_hash" not in policy_document_indexes:
        op.create_index(
            "ix_policy_documents_content_hash",
            "policy_documents",
            ["content_hash"],
        )

    # ------------------------------------------------------------------
    # policy_acceptances
    # ------------------------------------------------------------------
    inspector = sa.inspect(bind)

    policy_acceptance_columns = {
        column["name"]
        for column in inspector.get_columns("policy_acceptances")
    }

    columns = [
        (
            "session_id",
            sa.String(length=255),
        ),
        (
            "request_id",
            sa.String(length=120),
        ),
        (
            "action",
            sa.String(length=30),
        ),
        (
            "source",
            sa.String(length=40),
        ),
        (
            "authenticated",
            sa.Boolean(),
        ),
        (
            "auth_method",
            sa.String(length=40),
        ),
        (
            "content_hash",
            sa.String(length=64),
        ),
    ]

    for column_name, column_type in columns:
        if column_name not in policy_acceptance_columns:
            op.add_column(
                "policy_acceptances",
                sa.Column(
                    column_name,
                    column_type,
                    nullable=True,
                ),
            )

    # ------------------------------------------------------------------
    # Backfill existing policy acceptance records BEFORE enforcing
    # NOT NULL constraints.
    #
    # These defaults preserve the historical meaning of the existing
    # acceptance records created before the evidence metadata existed.
    # ------------------------------------------------------------------
    bind.execute(
        sa.text(
            """
            UPDATE policy_acceptances
            SET
                action = COALESCE(action, 'ACCEPTED'),
                source = COALESCE(source, 'web'),
                authenticated = COALESCE(authenticated, 1)
            WHERE
                action IS NULL
                OR source IS NULL
                OR authenticated IS NULL
            """
        )
    )

    # ------------------------------------------------------------------
    # SQLite does not support ALTER COLUMN ... SET NOT NULL directly.
    # Use Alembic batch mode so SQLite safely recreates the table while
    # preserving the existing data and constraints.
    # ------------------------------------------------------------------
    with op.batch_alter_table(
        "policy_acceptances",
        recreate="always",
    ) as batch_op:
        batch_op.alter_column(
            "action",
            existing_type=sa.String(length=30),
            nullable=False,
        )

        batch_op.alter_column(
            "source",
            existing_type=sa.String(length=40),
            nullable=False,
        )

        batch_op.alter_column(
            "authenticated",
            existing_type=sa.Boolean(),
            nullable=False,
        )

    # ------------------------------------------------------------------
    # Create the acceptance content-hash index if it does not already
    # exist.
    # ------------------------------------------------------------------
    inspector = sa.inspect(bind)

    policy_acceptance_indexes = {
        index["name"]
        for index in inspector.get_indexes("policy_acceptances")
    }

    if "ix_policy_acceptances_content_hash" not in policy_acceptance_indexes:
        op.create_index(
            "ix_policy_acceptances_content_hash",
            "policy_acceptances",
            ["content_hash"],
        )


def downgrade():
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # policy_acceptances
    # ------------------------------------------------------------------
    inspector = sa.inspect(bind)

    policy_acceptance_indexes = {
        index["name"]
        for index in inspector.get_indexes("policy_acceptances")
    }

    if "ix_policy_acceptances_content_hash" in policy_acceptance_indexes:
        op.drop_index(
            "ix_policy_acceptances_content_hash",
            table_name="policy_acceptances",
        )

    inspector = sa.inspect(bind)

    policy_acceptance_columns = {
        column["name"]
        for column in inspector.get_columns("policy_acceptances")
    }

    columns_to_remove = [
        "content_hash",
        "auth_method",
        "authenticated",
        "source",
        "action",
        "request_id",
        "session_id",
    ]

    existing_columns_to_remove = [
        column_name
        for column_name in columns_to_remove
        if column_name in policy_acceptance_columns
    ]

    if existing_columns_to_remove:
        with op.batch_alter_table(
            "policy_acceptances",
            recreate="always",
        ) as batch_op:
            for column_name in existing_columns_to_remove:
                batch_op.drop_column(column_name)

    # ------------------------------------------------------------------
    # policy_documents
    # ------------------------------------------------------------------
    inspector = sa.inspect(bind)

    policy_document_indexes = {
        index["name"]
        for index in inspector.get_indexes("policy_documents")
    }

    if "ix_policy_documents_content_hash" in policy_document_indexes:
        op.drop_index(
            "ix_policy_documents_content_hash",
            table_name="policy_documents",
        )

    inspector = sa.inspect(bind)

    policy_document_columns = {
        column["name"]
        for column in inspector.get_columns("policy_documents")
    }

    if "content_hash" in policy_document_columns:
        op.drop_column(
            "policy_documents",
            "content_hash",
        )