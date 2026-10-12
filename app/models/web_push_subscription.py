from app.extensions import db
from app.models.base import BaseModel


class WebPushSubscription(BaseModel):
    """Browser Web Push subscription owned by a FOCOST user."""

    __tablename__ = "web_push_subscriptions"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    endpoint = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    p256dh = db.Column(
        db.Text,
        nullable=False,
    )

    auth = db.Column(
        db.Text,
        nullable=False,
    )

    last_seen_at = db.Column(db.DateTime, nullable=True)

    is_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true(),
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "web_push_subscriptions",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )
