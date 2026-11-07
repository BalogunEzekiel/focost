"""Add individual communication recipients and sender identity."""
from alembic import op
import sqlalchemy as sa

revision = "ab31c9d8e702"
down_revision = "f1a9c7d2e604"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("announcements", sa.Column("recipient_emails", sa.Text(), nullable=True))
    op.add_column("announcements", sa.Column("sender_identity", sa.String(length=30), nullable=False, server_default="team"))

def downgrade():
    op.drop_column("announcements", "sender_identity")
    op.drop_column("announcements", "recipient_emails")
