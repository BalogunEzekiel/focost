from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel


class Expense(BaseModel):

    __tablename__ = "expenses"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    category = db.Column(
        db.String(100),
        nullable=False
    )

    merchant = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.String(255)
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    payment_method = db.Column(
        db.String(50),
        nullable=False
    )

    expense_date = db.Column(
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
            "expenses",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )

    def __repr__(self):
        return f"<Expense {self.category} - {self.amount}>"