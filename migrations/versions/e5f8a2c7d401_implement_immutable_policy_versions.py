"""Implement immutable policy version architecture.

Revision ID: e5f8a2c7d401
Revises: d1e7f3a9c402
"""

from alembic import op
import sqlalchemy as sa


revision = "e5f8a2c7d401"
down_revision = "d1e7f3a9c402"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # ================================================================
    # 1. policy_documents
    #
    # Rebuild explicitly because the existing SQLite schema contains
    # a unique slug constraint. The new architecture requires:
    #
    #   (slug, version) unique
    #   one current version per slug
    #   content_hash NOT NULL
    # ================================================================

    metadata = sa.MetaData()

    policy_documents_new = sa.Table(
        "policy_documents_new",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "public_id",
            sa.String(36),
            nullable=False,
        ),
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
            server_default=sa.text("1"),
        ),
        sa.Column(
            "slug",
            sa.String(80),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(200),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.String(40),
            nullable=False,
        ),
        sa.Column(
            "document_type",
            sa.String(60),
            nullable=False,
        ),
        sa.Column(
            "summary",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "content_html",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "effective_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "is_current",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "content_hash",
            sa.String(64),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "slug",
            "version",
            name="uq_policy_documents_slug_version",
        ),
    )

    policy_documents_new.create(bind)

    op.execute(
        sa.text(
            """
            INSERT INTO policy_documents_new (
                id,
                public_id,
                created_at,
                updated_at,
                is_active,
                slug,
                title,
                version,
                document_type,
                summary,
                content_html,
                effective_at,
                is_current,
                content_hash
            )
            SELECT
                id,
                public_id,
                created_at,
                updated_at,
                is_active,
                slug,
                title,
                version,
                document_type,
                summary,
                content_html,
                effective_at,
                is_current,
                content_hash
            FROM policy_documents
            """
        )
    )

    op.drop_table("policy_documents")
    op.rename_table("policy_documents_new", "policy_documents")

    op.create_index(
        "ix_policy_documents_slug",
        "policy_documents",
        ["slug"],
        unique=False,
    )

    op.create_index(
        "ix_policy_documents_document_type",
        "policy_documents",
        ["document_type"],
        unique=False,
    )

    op.create_index(
        "ix_policy_documents_is_current",
        "policy_documents",
        ["is_current"],
        unique=False,
    )

    op.create_index(
        "ix_policy_documents_content_hash",
        "policy_documents",
        ["content_hash"],
        unique=False,
    )

    op.create_index(
        "ix_policy_documents_public_id",
        "policy_documents",
        ["public_id"],
        unique=True,
    )

    op.create_index(
        "uq_policy_documents_current_slug",
        "policy_documents",
        ["slug"],
        unique=True,
        sqlite_where=sa.text("is_current = 1"),
    )

    # ================================================================
    # 2. policy_acceptances
    #
    # Explicitly declare the referenced tables in the same MetaData.
    # This is required for SQLAlchemy to compile the foreign keys.
    #
    # Existing acceptance records are copied unchanged.
    # ================================================================

    acceptance_metadata = sa.MetaData()

    # Lightweight reference tables used solely to resolve FKs.
    sa.Table(
        "users",
        acceptance_metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
    )

    sa.Table(
        "policy_documents",
        acceptance_metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
    )

    policy_acceptances_new = sa.Table(
        "policy_acceptances_new",
        acceptance_metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "public_id",
            sa.String(36),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "policy_id",
            sa.Integer(),
            sa.ForeignKey(
                "policy_documents.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "policy_version",
            sa.String(40),
            nullable=False,
        ),
        sa.Column(
            "accepted_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "ip_address",
            sa.String(64),
            nullable=True,
        ),
        sa.Column(
            "user_agent",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "session_id",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "request_id",
            sa.String(120),
            nullable=True,
        ),
        sa.Column(
            "action",
            sa.String(30),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(40),
            nullable=False,
        ),
        sa.Column(
            "authenticated",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "auth_method",
            sa.String(40),
            nullable=True,
        ),
        sa.Column(
            "content_hash",
            sa.String(64),
            nullable=False,
        ),
    )

    policy_acceptances_new.create(bind)

    op.execute(
        sa.text(
            """
            INSERT INTO policy_acceptances_new (
                id,
                public_id,
                created_at,
                updated_at,
                is_active,
                user_id,
                policy_id,
                policy_version,
                accepted_at,
                ip_address,
                user_agent,
                session_id,
                request_id,
                action,
                source,
                authenticated,
                auth_method,
                content_hash
            )
            SELECT
                id,
                public_id,
                created_at,
                updated_at,
                is_active,
                user_id,
                policy_id,
                policy_version,
                accepted_at,
                ip_address,
                user_agent,
                session_id,
                request_id,
                action,
                source,
                authenticated,
                auth_method,
                content_hash
            FROM policy_acceptances
            """
        )
    )

    op.drop_table("policy_acceptances")
    op.rename_table(
        "policy_acceptances_new",
        "policy_acceptances",
    )

    op.create_index(
        "ix_policy_acceptances_user_id",
        "policy_acceptances",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_policy_acceptances_policy_id",
        "policy_acceptances",
        ["policy_id"],
        unique=False,
    )

    op.create_index(
        "ix_policy_acceptances_content_hash",
        "policy_acceptances",
        ["content_hash"],
        unique=False,
    )

    op.create_index(
        "ix_policy_acceptances_public_id",
        "policy_acceptances",
        ["public_id"],
        unique=True,
    )


def downgrade():
    raise RuntimeError(
        "Downgrade of immutable policy version architecture is "
        "intentionally disabled. Restore a verified database backup "
        "instead of deleting historical policy-version evidence."
    )