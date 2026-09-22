"""Rename essential plan to basic

Revision ID: 245da8eb0855
Revises: 7b2f9e1a4c6d
Create Date: 2026-09-15 14:37:55.799604

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "245da8eb0855"
down_revision = "7b2f9e1a4c6d"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        UPDATE subscription_plans
        SET slug = 'basic',
            name = 'Basic'
        WHERE slug = 'essential'
        """
    )


def downgrade():
    op.execute(
        """
        UPDATE subscription_plans
        SET slug = 'essential',
            name = 'Essential'
        WHERE slug = 'basic'
        """
    )