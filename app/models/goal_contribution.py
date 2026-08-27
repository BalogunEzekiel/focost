from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel


class GoalContribution(BaseModel):
    __tablename__ = "goal_contributions"

    goal_id = db.Column(
        db.Integer,
        db.ForeignKey("goals.id"),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    contribution_date = db.Column(
        db.Date,
        nullable=False
    )

    note = db.Column(
        db.String(255)
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "goal_contributions",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )

    def __repr__(self):
        return (
            f"<GoalContribution "
            f"{self.goal_id} "
            f"₦{self.amount:,.2f}>"
        )