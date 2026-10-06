from app.extensions import db
from app.models.base import BaseModel
from app.utils.timezone import utc_now


class Announcement(BaseModel):
    """Centralized communications content and targeting policy."""

    __tablename__ = "announcements"

    title = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text, nullable=False)
    announcement_type = db.Column(db.String(30), nullable=False, default="notice", index=True)
    priority = db.Column(db.String(20), nullable=False, default="normal")
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)

    # Targeting: all, free_trial, basic, plus, pro, or user.
    audience = db.Column(db.String(30), nullable=False, default="all", index=True)
    target_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    # Channels are explicit so essential notices can remain independent of ads.
    in_app = db.Column(db.Boolean, nullable=False, default=True)
    dashboard_banner = db.Column(db.Boolean, nullable=False, default=False)
    flyer = db.Column(db.Boolean, nullable=False, default=False)
    email = db.Column(db.Boolean, nullable=False, default=False)
    push = db.Column(db.Boolean, nullable=False, default=False)

    action_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))

    starts_at = db.Column(db.DateTime, nullable=True, index=True)
    ends_at = db.Column(db.DateTime, nullable=True, index=True)

    published_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)

    target_user = db.relationship("User", foreign_keys=[target_user_id])
    published_by = db.relationship("User", foreign_keys=[published_by_id])

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
