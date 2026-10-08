"""Add immutable three-group RBAC identity.

Revision ID: r7c4e2a91f60
Revises: e8e26c587360
"""

from alembic import op
import sqlalchemy as sa


revision = "r7c4e2a91f60"
down_revision = "e8e26c587360"
branch_labels = None
depends_on = None


ROLE_GROUPS = ("super_admin", "admin", "user")


def _has_column(bind, table_name, column_name):
    inspector = sa.inspect(bind)
    return any(
        column["name"] == column_name
        for column in inspector.get_columns(table_name)
    )


def _has_index(bind, table_name, index_name):
    inspector = sa.inspect(bind)
    return any(
        index["name"] == index_name
        for index in inspector.get_indexes(table_name)
    )


def upgrade():
    bind = op.get_bind()

    if not _has_column(bind, "roles", "group_slug"):
        # SQLite requires batch recreation for a reliable NOT NULL column
        # with a value for existing rows.
        with op.batch_alter_table("roles", recreate="always") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "group_slug",
                    sa.String(length=30),
                    nullable=False,
                    server_default=sa.text("'admin'"),
                )
            )
            batch_op.create_check_constraint(
                "ck_roles_group_slug",
                "group_slug IN ('super_admin', 'admin', 'user')",
            )

    bind = op.get_bind()

    # The historical database contains three system roles plus custom
    # administrative roles. Every non-reserved role is an Admin-group role.
    bind.execute(
        sa.text(
            "UPDATE roles SET group_slug = 'super_admin' "
            "WHERE slug = 'super_admin'"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE roles SET group_slug = 'admin' "
            "WHERE slug = 'admin'"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE roles SET group_slug = 'user' "
            "WHERE slug = 'user'"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE roles SET group_slug = 'admin' "
            "WHERE slug NOT IN ('super_admin', 'admin', 'user')"
        )
    )

    bind.execute(
        sa.text(
            "UPDATE roles SET is_system = 1 "
            "WHERE slug IN ('super_admin', 'admin', 'user')"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE roles SET is_system = 0 "
            "WHERE slug NOT IN ('super_admin', 'admin', 'user')"
        )
    )

    if not _has_index(bind, "roles", "ix_roles_group_slug"):
        op.create_index(
            "ix_roles_group_slug",
            "roles",
            ["group_slug"],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()

    if _has_index(bind, "roles", "ix_roles_group_slug"):
        op.drop_index("ix_roles_group_slug", table_name="roles")

    if _has_column(bind, "roles", "group_slug"):
        with op.batch_alter_table("roles", recreate="always") as batch_op:
            batch_op.drop_constraint(
                "ck_roles_group_slug",
                type_="check",
            )
            batch_op.drop_column("group_slug")
