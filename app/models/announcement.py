from app.extensions import db
from app.models.base import BaseModel
from app.utils.timezone import utc_now
import json


class Announcement(BaseModel):
    """Centralized communications content and targeting policy."""

    __tablename__ = "announcements"

    title = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text, nullable=False)
    announcement_type = db.Column(db.String(30), nullable=False, default="notice", index=True)
    priority = db.Column(db.String(20), nullable=False, default="normal")
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)

    # Targeting: all, super_admin, admin, user, free_trial, basic, plus, pro,
    # subscription_expired, inactive_user (pending normal-user activation only).
    audience = db.Column(db.String(30), nullable=False, default="all", index=True)
    # JSON array of audience slugs; audience remains as a legacy fallback.
    audience_groups = db.Column(db.Text, nullable=True)
    email_signature_enabled = db.Column(db.Boolean, nullable=False, default=True)
    email_signature = db.Column(db.Text, nullable=True)
    message_background = db.Column(db.String(30), nullable=False, default="plain")
    target_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    # Channels are explicit so essential notices can remain independent of ads.
    in_app = db.Column(db.Boolean, nullable=False, default=True)
    dashboard_banner = db.Column(db.Boolean, nullable=False, default=False)
    flyer = db.Column(db.Boolean, nullable=False, default=False)
    email = db.Column(db.Boolean, nullable=False, default=False)
    push = db.Column(db.Boolean, nullable=False, default=False)

    action_url = db.Column(db.String(500))
    action_label = db.Column(db.String(60), nullable=True)
    image_url = db.Column(db.String(500))

    starts_at = db.Column(db.DateTime, nullable=True, index=True)
    ends_at = db.Column(db.DateTime, nullable=True, index=True)

    published_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)

    target_user = db.relationship("User", foreign_keys=[target_user_id])
    published_by = db.relationship("User", foreign_keys=[published_by_id])

    @property
    def audiences(self):
        try:
            values = json.loads(self.audience_groups or "[]")
            return values if isinstance(values, list) and values else [self.audience or "all"]
        except (TypeError, ValueError):
            return [self.audience or "all"]

    @property
    def is_live(self):
        now = utc_now()
        return (
            self.is_active
            and self.status == "published"
            and (not self.starts_at or self.starts_at <= now)
            and (not self.ends_at or self.ends_at > now)
        )

    @property
    def is_advertisement(self):
        return self.announcement_type == "advertisement"
