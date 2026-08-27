from app.extensions import db

from app.models.mixins import (
    TimestampMixin,
    PublicIDMixin,
    ActiveMixin
)


class BaseModel(
    db.Model,
    TimestampMixin,
    PublicIDMixin,
    ActiveMixin
):
    """
    Base model shared by every database model.
    """

    __abstract__ = True

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    def to_dict(self):

        return {
            "id": self.public_id,
            "created_at": self.created_at.isoformat()
            if self.created_at else None,
            "updated_at": self.updated_at.isoformat()
            if self.updated_at else None,
            "is_active": self.is_active
        }