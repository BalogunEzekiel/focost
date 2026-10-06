from app.extensions import db
from app.models.base import BaseModel


class PushDevice(BaseModel):
    """Registered mobile/browser push endpoint.

    The token is provider-neutral so FCM/APNs can be attached without
    changing the communications domain model.
    """

    __tablename__ = "push_devices"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform = db.Column(db.String(20), nullable=False)
    token = db.Column(db.Text, nullable=False, unique=True, index=True)
    provider = db.Column(db.String(30), nullable=False, default="fcm")
    app_version = db.Column(db.String(40))
    last_seen_at = db.Column(db.DateTime)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)

    user = db.relationship(
        "User",
        backref=db.backref("push_devices", lazy=True, cascade="all, delete-orphan"),
    )
