"""Persistent configuration and staging records for FOCOST integrations."""
from app.extensions import db
from app.models.base import BaseModel


class FeaturePolicy(BaseModel):
    __tablename__ = "feature_policies"
    module_key = db.Column(db.String(80), nullable=False, unique=True, index=True)
    label = db.Column(db.String(120), nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    allowed_roles_json = db.Column(db.Text, nullable=False, default='["user"]')
    allowed_plans_json = db.Column(db.Text, nullable=False, default='["basic","plus","pro","free trial"]')
    operations_json = db.Column(db.Text, nullable=False, default='["view","create","edit","delete","export"]')
    delegated_roles_json = db.Column(db.Text, nullable=False, default='[]')
    config_json = db.Column(db.Text, nullable=False, default='{}')

    def json_list(self, field):
        import json
        try:
            value = json.loads(getattr(self, field) or "[]")
            return value if isinstance(value, list) else []
        except (TypeError, ValueError):
            return []

    def config(self):
        import json
        try:
            value = json.loads(self.config_json or "{}")
            return value if isinstance(value, dict) else {}
        except (TypeError, ValueError):
            return {}


class DocumentImport(BaseModel):
    __tablename__ = "document_imports"
    __table_args__ = (db.UniqueConstraint("user_id", "content_sha256", name="uq_document_import_user_checksum"),)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    import_type = db.Column(db.String(24), nullable=False, index=True)  # receipt / statement
    original_name = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.String(500), nullable=False)
    content_sha256 = db.Column(db.String(64), nullable=False, index=True)
    status = db.Column(db.String(24), nullable=False, default="review")  # review / partial / imported / failed
    extracted_json = db.Column(db.Text, nullable=False, default='{"transactions":[]}')
    error_message = db.Column(db.String(500))
    user = db.relationship("User", backref=db.backref("document_imports", lazy=True, cascade="all, delete-orphan"))

    def extracted(self):
        import json
        try:
            value = json.loads(self.extracted_json or "{}")
            return value if isinstance(value, dict) else {"transactions": []}
        except (TypeError, ValueError):
            return {"transactions": []}


class BankConnection(BaseModel):
    """Read-only bank connection. Provider references and cached balances are encrypted at rest."""
    __tablename__ = "bank_connections"
    __table_args__ = (db.UniqueConstraint("user_id", "provider_key", "account_fingerprint", name="uq_bank_connection_user_provider_fingerprint"),)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_key = db.Column(db.String(80), nullable=False)
    provider_account_id = db.Column(db.String(180))
    account_fingerprint = db.Column(db.String(64), nullable=False)
    account_name = db.Column(db.String(180))
    account_mask = db.Column(db.String(12))
    currency = db.Column(db.String(8))
    encrypted_balance = db.Column(db.Text)
    encrypted_access_token = db.Column(db.Text)
    encrypted_refresh_token = db.Column(db.Text)
    status = db.Column(db.String(24), nullable=False, default="pending")
    last_synced_at = db.Column(db.DateTime)
    last_error = db.Column(db.String(500))
    user = db.relationship("User", backref=db.backref("bank_connections", lazy=True, cascade="all, delete-orphan"))

    @property
    def current_balance(self):
        if not self.encrypted_balance:
            return None
        try:
            from app.services.bank_security_service import BankSecurityService
            return float(BankSecurityService.decrypt(self.encrypted_balance))
        except Exception:
            return None


class BankSyncRecord(BaseModel):
    __tablename__ = "bank_sync_records"
    connection_id = db.Column(db.Integer, db.ForeignKey("bank_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_transaction_id = db.Column(db.String(180), nullable=False)
    transaction_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # positive credit, negative debit
    currency = db.Column(db.String(8))
    fingerprint = db.Column(db.String(64), nullable=False)
    raw_json = db.Column(db.Text, nullable=False, default="{}")
    status = db.Column(db.String(24), nullable=False, default="review")
    __table_args__ = (db.UniqueConstraint("connection_id", "provider_transaction_id", name="uq_bank_sync_provider_txn"),)
    connection = db.relationship("BankConnection", backref=db.backref("sync_records", lazy=True, cascade="all, delete-orphan"))


# Delete retained source files when their import row is deleted through ORM cascades.
from sqlalchemy import event
from pathlib import Path
from flask import has_app_context, current_app

@event.listens_for(DocumentImport, "after_delete")
def _remove_document_import_file(mapper, connection, target):
    try:
        path = Path(target.stored_path)
        # Only remove files rooted under the configured private import directory.
        if not has_app_context():
            return
        root = Path(current_app.config.get("INTEGRATION_UPLOAD_DIR", "instance/private_imports")).resolve()
        resolved = path.resolve()
        if resolved == root or root not in resolved.parents:
            return
        path.unlink(missing_ok=True)
    except Exception:
        # A failed filesystem cleanup must not undo a user's account deletion.
        import logging
        logging.getLogger(__name__).exception("Failed to delete private document import source")
