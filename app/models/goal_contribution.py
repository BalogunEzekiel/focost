from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel


class GoalContribution(BaseModel):
    __tablename__ = "goal_contributions"
    __table_args__ = (db.CheckConstraint("amount > 0", name="ck_goal_contributions_amount_positive"),)

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

    # Every contribution is backed by a cash-outflow transaction.
    expense_id = db.Column(
        db.Integer,
        db.ForeignKey("expenses.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True
    )

    expense = db.relationship(
        "Expense",
        foreign_keys=[expense_id],
        backref=db.backref("goal_contribution_link", uselist=False)
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