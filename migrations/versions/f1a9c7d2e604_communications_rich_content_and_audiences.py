"""Add rich communications content and multi-audience targeting."""
from alembic import op
import sqlalchemy as sa

revision = "f1a9c7d2e604"
down_revision = "c784ab6c1139"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("announcements") as batch_op:
        batch_op.add_column(sa.Column("audience_groups", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("action_label", sa.String(length=60), nullable=True))
        batch_op.add_column(sa.Column("email_signature_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("email_signature", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("message_background", sa.String(length=30), nullable=False, server_default="plain"))


def downgrade():
    with op.batch_alter_table("announcements") as batch_op:
        batch_op.drop_column("message_background")
        batch_op.drop_column("action_label")
        batch_op.drop_column("email_signature")
        batch_op.drop_column("email_signature_enabled")
        batch_op.drop_column("audience_groups")
