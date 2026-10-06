"""Restore missing user creator hierarchy schema.

Revision ID: 23c38dd99401
Revises: e5f8a2c7d401

This migration repairs schema drift where the SQLAlchemy User model
contains created_by_id but the physical SQLite users table does not.

The repair preserves all existing user records. The new column is
nullable, so existing users receive NULL and no existing User.id or
related data is changed.
"""

from alembic import op
import sqlalchemy as sa


revision = "23c38dd99401"
down_revision = "e5f8a2c7d401"
branch_labels = None
depends_on = None


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


def _has_creator_foreign_key(bind):
    inspector = sa.inspect(bind)

    for fk in inspector.get_foreign_keys("users"):
        if (
            fk.get("referred_table") == "users"
            and fk.get("constrained_columns") == ["created_by_id"]
            and fk.get("referred_columns") == ["id"]
        ):
            return True

    return False


def upgrade():
    bind = op.get_bind()

    column_exists = _has_column(
        bind,
        "users",
        "created_by_id",
    )

    foreign_key_exists = (
        _has_creator_foreign_key(bind)
        if column_exists
        else False
    )

    # SQLite requires batch table recreation for safely adding
    # the self-referencing foreign key.
    if not column_exists or not foreign_key_exists:
        with op.batch_alter_table(
            "users",
            schema=None,
            recreate="always",
        ) as batch_op:

            if not column_exists:
                batch_op.add_column(
                    sa.Column(
                        "created_by_id",
                        sa.Integer(),
                        nullable=True,
                    )
                )

            if not foreign_key_exists:
                batch_op.create_foreign_key(
                    "fk_users_created_by_id",
                    "users",
                    ["created_by_id"],
                    ["id"],
                    ondelete="SET NULL",
                )

    # Reinspect after any SQLite batch recreation.
    bind = op.get_bind()

    if not _has_index(
        bind,
        "users",
        "ix_users_created_by_id",
    ):
        op.create_index(
            "ix_users_created_by_id",
            "users",
            ["created_by_id"],
            unique=False,
        )


def downgrade():
    # Intentionally non-destructive.
    #
    # Removing this schema automatically could destroy administrator
    # provisioning relationships. Any rollback should therefore be
    # performed explicitly after reviewing affected data.
    pass