"""Add administrator provisioning metadata.

Revision ID: f4b2c8d9e701
Revises: e2a7c4f9b601
"""

from alembic import op
import sqlalchemy as sa


revision = "f4b2c8d9e701"
down_revision = "e2a7c4f9b601"
branch_labels = None
depends_on = None


def upgrade():
    # This migration partially ran before failing on SQLite:
    # - users.created_by_id already exists
    # - ix_users_created_by_id already exists
    # - the self-referencing foreign key does not exist
    #
    # Therefore, do not add the column/index again. Use SQLite batch
    # mode to add the missing self-referencing foreign key safely.

    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.create_foreign_key(
            "fk_users_created_by_id",
            "users",
            local_cols=["created_by_id"],
            remote_cols=["id"],
            ondelete="SET NULL",
        )


def downgrade():
    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.drop_constraint(
            "fk_users_created_by_id",
            type_="foreignkey",
        )

    # The column and index were created by the original partial execution
    # of this migration, so remove them during downgrade as well.
    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.drop_index("ix_users_created_by_id")
        batch_op.drop_column("created_by_id")