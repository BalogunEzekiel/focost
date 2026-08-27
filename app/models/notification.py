from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel

class Notification(BaseModel):
    """
    Stores application notifications for each user.

    Examples:
        - Budget exceeded
        - Goal achieved
        - Bill due
        - Low balance warning
        - AI insight
    """

    __tablename__ = "notifications"

    __table_args__ = (

        db.Index(
            "idx_notification_user_read",
            "user_id",
            "is_read"
        ),

        db.Index(
            "idx_notification_user_created",
            "user_id",
            "created_at"
        ),

        db.Index(
            "idx_notification_unique",
            "user_id",
            "unique_key"
        ),

    )

    # ---------------------------------------------------------
    # Ownership
    # ---------------------------------------------------------

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # ---------------------------------------------------------
    # Notification Content
    # ---------------------------------------------------------

    title = db.Column(
        db.String(150),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    # ---------------------------------------------------------
    # Notification Classification
    # ---------------------------------------------------------

    notification_type = db.Column(
        db.String(50),
        nullable=False,
        default="general",
        index=True
    )

    source = db.Column(
        db.String(50),
        default="System"
    )

    priority = db.Column(
        db.String(20),
        nullable=False,
        default="normal"
    )

    # ---------------------------------------------------------
    # Appearance
    # ---------------------------------------------------------

    level = db.Column(
        db.String(20),
        nullable=False,
        default="info"
    )

    icon = db.Column(
        db.String(50),
        default="bi-bell-fill"
    )

    action_url = db.Column(
        db.String(255)
    )

    # ---------------------------------------------------------
    # Duplicate Prevention
    # ---------------------------------------------------------

    unique_key = db.Column(
        db.String(255),
        index=True
    )

    # ---------------------------------------------------------
    # Status
    # ---------------------------------------------------------

    is_read = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    is_deleted = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    # ---------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------

    user = db.relationship(
        "User",
        backref=db.backref(
            "notifications",
            lazy="dynamic",
            cascade="all, delete-orphan"
        )
    )

    # ---------------------------------------------------------
    # Human Readable Time
    # ---------------------------------------------------------

    @property
    def time(self):

        if not self.created_at:
            return ""

        diff = datetime.utcnow() - self.created_at

        seconds = int(diff.total_seconds())

        if seconds < 60:
            return "Just now"

        minutes = seconds // 60

        if minutes < 60:
            return f"{minutes} min ago"

        hours = minutes // 60

        if hours < 24:
            return f"{hours} hr ago"

        days = hours // 24

        if days < 7:
            return f"{days} day{'s' if days != 1 else ''} ago"

        if days < 30:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"

        return self.created_at.strftime("%d %b %Y")

    # ---------------------------------------------------------
    # Mark Read
    # ---------------------------------------------------------

    def mark_as_read(self):

        if not self.is_read:

            self.is_read = True
            self.read_at = datetime.utcnow()

    # ---------------------------------------------------------
    # Soft Delete
    # ---------------------------------------------------------

    def soft_delete(self):

        self.is_deleted = True

    # ---------------------------------------------------------
    # Serialization
    # ---------------------------------------------------------

    def to_dict(self):

        return {

            "id": self.id,

            "title": self.title,

            "message": self.message,

            "notification_type": self.notification_type,

            "priority": self.priority,

            "source": self.source,

            "level": self.level,

            "icon": self.icon,

            "is_read": self.is_read,

            "is_deleted": self.is_deleted,

            "action_url": self.action_url,

            "unique_key": self.unique_key,

            "time": self.time,

            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),

            "read_at": (
                self.read_at.isoformat()
                if self.read_at
                else None
            )

        }

    # ---------------------------------------------------------
    # Representation
    # ---------------------------------------------------------

    def __repr__(self):

        return (
            f"<Notification("
            f"id={self.id}, "
            f"user={self.user_id}, "
            f"type='{self.notification_type}', "
            f"title='{self.title}', "
            f"read={self.is_read}"
            f")>"
        )