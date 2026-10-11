"""Add integration feature policies, private document staging and read-only bank staging."""
from alembic import op
import sqlalchemy as sa

revision = "f9c2a6d8e401"
down_revision = "r7c4e2a91f60"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("feature_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("module_key", sa.String(length=80), nullable=False, unique=True),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allowed_roles_json", sa.Text(), nullable=False, server_default='["user"]'),
        sa.Column("allowed_plans_json", sa.Text(), nullable=False, server_default='["basic","plus","pro","free trial"]'),
        sa.Column("operations_json", sa.Text(), nullable=False, server_default='["view","create","edit","delete","export"]'),
        sa.Column("delegated_roles_json", sa.Text(), nullable=False, server_default='[]'),
        sa.Column("config_json", sa.Text(), nullable=False, server_default='{}'))
    op.create_index("ix_feature_policies_module_key", "feature_policies", ["module_key"], unique=False)
    op.create_index("ix_feature_policies_public_id", "feature_policies", ["public_id"], unique=False)

    op.create_table("document_imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("import_type", sa.String(length=24), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="review"),
        sa.Column("extracted_json", sa.Text(), nullable=False, server_default='{"transactions":[]}'),
        sa.Column("error_message", sa.String(length=500)),
        sa.UniqueConstraint("user_id", "content_sha256", name="uq_document_import_user_checksum"))
    op.create_index("ix_document_imports_user_id", "document_imports", ["user_id"])
    op.create_index("ix_document_imports_import_type", "document_imports", ["import_type"])
    op.create_index("ix_document_imports_content_sha256", "document_imports", ["content_sha256"])
    op.create_index("ix_document_imports_public_id", "document_imports", ["public_id"], unique=False)

    op.create_table("bank_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_key", sa.String(length=80), nullable=False),
        sa.Column("provider_account_id", sa.String(length=180)),
        sa.Column("account_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("account_name", sa.String(length=180)),
        sa.Column("account_mask", sa.String(length=12)),
        sa.Column("currency", sa.String(length=8)),
        sa.Column("encrypted_balance", sa.Text()),
        sa.Column("encrypted_access_token", sa.Text()),
        sa.Column("encrypted_refresh_token", sa.Text()),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("last_synced_at", sa.DateTime()),
        sa.Column("last_error", sa.String(length=500)),
        sa.UniqueConstraint("user_id", "provider_key", "account_fingerprint", name="uq_bank_connection_user_provider_fingerprint"))
    op.create_index("ix_bank_connections_user_id", "bank_connections", ["user_id"])
    op.create_index("ix_bank_connections_public_id", "bank_connections", ["public_id"], unique=False)

    op.create_table("bank_sync_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("connection_id", sa.Integer(), sa.ForeignKey("bank_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_transaction_id", sa.String(length=180), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8)),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("raw_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="review"),
        sa.UniqueConstraint("connection_id", "provider_transaction_id", name="uq_bank_sync_provider_txn"))
    op.create_index("ix_bank_sync_records_connection_id", "bank_sync_records", ["connection_id"])
    op.create_index("ix_bank_sync_records_public_id", "bank_sync_records", ["public_id"], unique=False)

def downgrade():
    op.drop_table("bank_sync_records")
    op.drop_table("bank_connections")
    op.drop_table("document_imports")
    op.drop_table("feature_policies")
