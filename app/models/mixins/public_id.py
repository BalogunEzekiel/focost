import uuid

from app.extensions import db


class PublicIDMixin:

    public_id = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4())
    )