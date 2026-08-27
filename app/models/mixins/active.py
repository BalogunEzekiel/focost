from app.extensions import db


class ActiveMixin:
    """
    Adds an active/inactive flag to models.
    """

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )