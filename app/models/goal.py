from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel


class Goal(BaseModel):
    __tablename__ = "goals"
    __table_args__ = (db.CheckConstraint("target_amount > 0", name="ck_goals_target_amount_positive"),)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    title = db.Column(
        db.String(150),
        nullable=False
    )

    goal_type = db.Column(
        db.String(100),
        nullable=False
    )

    target_amount = db.Column(
        db.Float,
        nullable=False
    )

    target_date = db.Column(
        db.Date,
        nullable=False
    )

    priority = db.Column(
        db.String(20),
        default="Medium"
    )

    status = db.Column(
        db.String(20),
        default="In Progress"
    )

    notes = db.Column(
        db.Text
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "goals",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )

    contributions = db.relationship(
        "GoalContribution",
        backref="goal",
        lazy=True,
        cascade="all, delete-orphan"
    )

    completed_at = db.Column(
        db.DateTime
    )

    reminder = db.Column(
        db.Boolean,
        default=True
    )

    @property
    def saved_amount(self):
        return min(
            float(self.target_amount or 0),
            sum(float(contribution.amount or 0) for contribution in self.contributions if contribution.is_active)
        )

    @property
    def remaining_amount(self):
        return max(
            self.target_amount - self.saved_amount,
            0
        )

    @property
    def percentage_completed(self):
        if self.target_amount <= 0:
            return 0

        return round(
            (self.saved_amount / self.target_amount) * 100,
            2
        )

    @property
    def progress_status(self):

        if self.percentage_completed >= 100:
            return "Completed"

        if (
            self.target_date < datetime.utcnow().date()
            and self.percentage_completed < 100
        ):
            return "Overdue"

        if self.percentage_completed >= 75:
            return "On Track"

        return "In Progress"

    @property
    def progress_percentage(self):

        if self.target_amount <= 0:
            return 0
        
        pct = (self.saved_amount / self.target_amount) * 100

        return round(min(pct, 100), 2)
    
    @property
    def days_remaining(self):
        if self.percentage_completed >= 100:
            return 0
        return (self.target_date - datetime.utcnow().date()).days
    
    @property
    def monthly_contribution(self):
        if self.days_remaining <= 0:
            return self.remaining_amount

        months = max(self.days_remaining / 30, 1)

        return round(self.remaining_amount / months, 2)

    @property
    def percentage(self):
        return self.progress_percentage
    
    @property
    def saved(self):
        return self.saved_amount


    @property
    def remaining(self):
        return self.remaining_amount


    @property
    def target(self):
        return self.target_amount
    
