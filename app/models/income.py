from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel

class Income(BaseModel):
    __tablename__ = "income"
    __table_args__ = (db.CheckConstraint("amount > 0", name="ck_income_amount_positive"),)

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

    # Distinguishes ordinary income from investment-generated cash inflows.
    # Values: income, investment_gain, investment_liquidation.
    transaction_class = db.Column(
        db.String(30),
        nullable=False,
        default="income",
        index=True
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