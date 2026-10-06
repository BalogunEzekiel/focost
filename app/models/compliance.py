from sqlalchemy import event, inspect

from app.extensions import db
from app.models.base import BaseModel


class PolicyDocument(BaseModel):
    """
    Immutable, versioned compliance policy document.

    Each published policy version is a separate database row.

    Example:
        terms 1.1
        terms 1.2
        terms 1.3

    Historical policy content and identity must never be overwritten.

    The only mutable field on an existing policy document is
    ``is_current``. This is required when a newer version is published:
        1.1 -> historical
        1.2 -> current
    """

    __tablename__ = "policy_documents"

    slug = db.Column(
        db.String(80),
        nullable=False,
        index=True,
    )

    title = db.Column(
        db.String(200),
        nullable=False,
    )

    version = db.Column(
        db.String(40),
        nullable=False,
    )

    document_type = db.Column(
        db.String(60),
        nullable=False,
        index=True,
    )

    summary = db.Column(
        db.Text,
        nullable=True,
    )

    content_html = db.Column(
        db.Text,
        nullable=False,
    )

    effective_at = db.Column(
        db.DateTime,
        nullable=False,
    )

    is_current = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    content_hash = db.Column(
        db.String(64),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "slug",
            "version",
            name="uq_policy_documents_slug_version",
        ),
        db.Index(
            "uq_policy_documents_current_slug",
            "slug",
            unique=True,
            sqlite_where=db.text("is_current = 1"),
        ),
    )


@event.listens_for(PolicyDocument, "before_update")
def _prevent_policy_document_mutation(mapper, connection, target):
    """
    Prevent modification of an existing published policy document.

    Allowed:
        - is_current

    Also ignored:
        - updated_at

    Everything else is immutable once the row exists.

    This permits the legitimate publication transition:

        old 1.1: is_current=True  -> False
        new 1.2: is_current=False -> True

    while preventing changes to:
        slug
        title
        version
        document_type
        summary
        content_html
        effective_at
        content_hash
        is_active
    """

    state = inspect(target)

    allowed_mutable_fields = {
        "is_current",
        "updated_at",
    }

    changed_fields = []

    for attribute in state.mapper.column_attrs:
        field_name = attribute.key

        if field_name in allowed_mutable_fields:
            continue

        history = state.attrs[field_name].history

        if history.has_changes():
            changed_fields.append(field_name)

    if changed_fields:
        raise ValueError(
            "Immutable policy violation: published policy documents "
            "cannot be modified. "
            f"Attempted changes: {', '.join(sorted(changed_fields))}. "
            "Publish a new policy version instead."
        )


@event.listens_for(PolicyDocument, "before_delete")
def _prevent_policy_document_deletion(mapper, connection, target):
    """
    Prevent deletion of policy-version evidence.

    Historical policy documents must remain available because existing
    PolicyAcceptance records reference the exact policy version accepted
    by the user.
    """

    raise ValueError(
        "Immutable policy violation: policy documents cannot be deleted. "
        "Historical policy versions are permanent compliance evidence."
    )


class PolicyAcceptance(BaseModel):
    """
    Immutable evidence that a user accepted a specific policy version.

    policy_id + policy_version + content_hash identify exactly what
    the user accepted.
    """

    __tablename__ = "policy_acceptances"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    policy_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "policy_documents.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    policy_version = db.Column(
        db.String(40),
        nullable=False,
    )

    accepted_at = db.Column(
        db.DateTime,
        nullable=False,
    )

    ip_address = db.Column(
        db.String(64),
        nullable=True,
    )

    user_agent = db.Column(
        db.Text,
        nullable=True,
    )

    session_id = db.Column(
        db.String(255),
        nullable=True,
    )

    request_id = db.Column(
        db.String(120),
        nullable=True,
    )

    action = db.Column(
        db.String(30),
        nullable=False,
        default="ACCEPTED",
    )

    source = db.Column(
        db.String(40),
        nullable=False,
        default="web",
    )

    authenticated = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    auth_method = db.Column(
        db.String(40),
        nullable=True,
    )

    content_hash = db.Column(
        db.String(64),
        nullable=False,
        index=True,
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "policy_acceptances",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    policy = db.relationship(
        "PolicyDocument",
    )


class AuthToken(BaseModel):
    __tablename__ = "auth_tokens"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash = db.Column(
        db.String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    purpose = db.Column(
        db.String(40),
        nullable=False,
        index=True,
    )

    expires_at = db.Column(
        db.DateTime,
        nullable=False,
        index=True,
    )

    used_at = db.Column(
        db.DateTime,
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "auth_tokens",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )


class AuthThrottle(BaseModel):
    __tablename__ = "auth_throttles"

    throttle_key = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    attempts = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    window_started_at = db.Column(
        db.DateTime,
        nullable=False,
    )

    blocked_until = db.Column(
        db.DateTime,
        index=True,
    )


class DocumentArchive(BaseModel):
    __tablename__ = "document_archive"

    title = db.Column(
        db.String(255),
        nullable=False,
    )

    document_type = db.Column(
        db.String(80),
        nullable=False,
        index=True,
    )

    description = db.Column(
        db.Text,
    )

    version = db.Column(
        db.String(60),
    )

    effective_date = db.Column(
        db.Date,
    )

    original_filename = db.Column(
        db.String(255),
        nullable=False,
    )

    stored_filename = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
    )

    storage_path = db.Column(
        db.String(1000),
        nullable=False,
    )

    mime_type = db.Column(
        db.String(150),
    )

    file_size = db.Column(
        db.BigInteger,
        nullable=False,
        default=0,
    )

    sha256 = db.Column(
        db.String(64),
        nullable=False,
        index=True,
    )

    uploaded_by_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    uploaded_by = db.relationship(
        "User",
        foreign_keys=[uploaded_by_id],
    )