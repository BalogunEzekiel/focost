from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel

class Income(BaseModel):
    __tablename__ = "income"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    source = db.Column(
        db.String(150),
        nullable=False
    )

    category = db.Column(
        db.String(100),
        nullable=False
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    received_date = db.Column(
        db.Date,
        nullable=False
    )

    notes = db.Column(
        db.Text
    )

    recurring = db.Column(
        db.Boolean,
        default=False
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "income",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )

    def __repr__(self):
        return f"<Income {self.source} - {self.amount}>"