from app.extensions import db
from app.utils.timezone import utc_now


class TimestampMixin:

    created_at = db.Column(
        db.DateTime,
        default=utc_now,
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False
    )