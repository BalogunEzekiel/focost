"""Enhance notification lifecycle fields."""
from alembic import op
import sqlalchemy as sa
revision = "9c3e1a6d7f2b"
down_revision = "8f4d2a7c1b9e"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(sa.Column("read_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("dismissed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_notifications_expires_at", ["expires_at"], unique=False)

def downgrade():
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_index("ix_notifications_expires_at")
        batch_op.drop_column("expires_at")
        batch_op.drop_column("dismissed_at")
        batch_op.drop_column("read_at")
