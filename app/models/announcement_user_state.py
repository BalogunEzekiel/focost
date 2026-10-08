from app.extensions import db
from app.models.base import BaseModel
from app.utils.timezone import utc_now


class AnnouncementUserState(BaseModel):
    """
    Stores per-user interaction state for announcements.

    An announcement remains globally managed by the Announcement model.
    This table only records how an individual user interacted with it.
    """

    __tablename__ = "announcement_user_states"

    announcement_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "announcements.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )

    dismissed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    read_at = db.Column(
        db.DateTime,
        nullable=True
    )

    announcement = db.relationship(
        "Announcement",
        backref="user_states"
    )

    user = db.relationship(
        "User",
        backref="announcement_states"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "announcement_id",
            "user_id",
            name="uq_announcement_user_state"
        ),
    )

    @property
    def is_dismissed(self):
        return self.dismissed_at is not None

    def dismiss(self):
        self.dismissed_at = utc_now()