"""Add compliance, policy acceptance, auth recovery and document archive controls.

Revision ID: c4d8e2f1a9b3
Revises: b7c4e2a91f60
"""
from alembic import op
import sqlalchemy as sa

revision = "c4d8e2f1a9b3"
down_revision = "b7c4e2a91f60"
branch_labels = None
depends_on = None


def upgrade():
    # SQLite requires a table rebuild for this alteration. Add the column
    # temporarily as nullable with a server default so existing rows receive
    # a value during the rebuild.
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "auth_version",
                sa.Integer(),
                nullable=True,
                server_default="1",
            )
        )

    # Existing accounts were created under the pre-verification
    # authentication model. Preserve access for those users; verification
    # is mandatory for new registrations.
    op.execute(
        sa.text(
            "UPDATE users "
            "SET email_verified = TRUE "
            "WHERE email_verified IS NULL OR email_verified = FALSE"
        )
    )

    # Ensure every existing account has the authentication version.
    op.execute(
        sa.text(
            "UPDATE users "
            "SET auth_version = 1 "
            "WHERE auth_version IS NULL"
        )
    )

    # Enforce the final schema after all existing rows have been populated.
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "auth_version",
            existing_type=sa.Integer(),
            nullable=False,
            server_default=None,
        )

    op.create_table(
        "policy_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
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
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("document_type", sa.String(60), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column("effective_at", sa.DateTime(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_policy_documents_slug", "policy_documents", ["slug"], unique=True)
    op.create_index(
        "ix_policy_documents_document_type",
        "policy_documents",
        ["document_type"],
    )
    op.create_index(
        "ix_policy_documents_is_current",
        "policy_documents",
        ["is_current"],
    )

    op.create_table(
        "policy_acceptances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
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
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.String(40), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("user_agent", sa.Text()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_id"], ["policy_documents.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_policy_acceptances_user_id",
        "policy_acceptances",
        ["user_id"],
    )
    op.create_index(
        "ix_policy_acceptances_policy_id",
        "policy_acceptances",
        ["policy_id"],
    )

    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
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
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("purpose", sa.String(40), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])
    op.create_index(
        "ix_auth_tokens_token_hash",
        "auth_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index("ix_auth_tokens_purpose", "auth_tokens", ["purpose"])
    op.create_index("ix_auth_tokens_expires_at", "auth_tokens", ["expires_at"])

    op.create_table(
        "auth_throttles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
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
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("throttle_key", sa.String(255), nullable=False, unique=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.DateTime(), nullable=False),
        sa.Column("blocked_until", sa.DateTime()),
    )
    op.create_index(
        "ix_auth_throttles_throttle_key",
        "auth_throttles",
        ["throttle_key"],
        unique=True,
    )
    op.create_index(
        "ix_auth_throttles_blocked_until",
        "auth_throttles",
        ["blocked_until"],
    )

    op.create_table(
        "document_archive",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
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
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("document_type", sa.String(80), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("version", sa.String(60)),
        sa.Column("effective_date", sa.Date()),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False, unique=True),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("mime_type", sa.String(150)),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer()),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_document_archive_document_type",
        "document_archive",
        ["document_type"],
    )
    op.create_index(
        "ix_document_archive_sha256",
        "document_archive",
        ["sha256"],
    )
    op.create_index(
        "ix_document_archive_uploaded_by_id",
        "document_archive",
        ["uploaded_by_id"],
    )

def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("auth_version")

    op.drop_table("document_archive")
    op.drop_table("auth_throttles")
    op.drop_table("auth_tokens")
    op.drop_table("policy_acceptances")
    op.drop_table("policy_documents")
