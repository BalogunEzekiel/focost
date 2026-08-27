from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel

class Budget(BaseModel):
    
    __tablename__ = "budgets"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
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

    period = db.Column(
        db.String(20),
        default="Monthly"
    )

    start_date = db.Column(
        db.Date,
        nullable=False
    )

    end_date = db.Column(
        db.Date,
        nullable=False
    )

    spent = db.Column(
        db.Float,
        default=0
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "budgets",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )

    @property
    def remaining(self):
        return max(self.amount - self.spent, 0)


    @property
    def percentage_used(self):
        if self.amount <= 0:
            return 0
        return round((self.spent / self.amount) * 100, 2)


    @property
    def status(self):
        pct = self.percentage_used

        if pct >= 100:
            return "Exceeded"
        elif pct >= 90:
            return "Critical"
        elif pct >= 75:
            return "Warning"
        else:
            return "Healthy"
        
    @property
    def risk(self):

        pct = self.percentage_used

        if pct >= 100:
            return "Critical"

        elif pct >= 90:
            return "High"

        elif pct >= 75:
            return "Medium"

        return "Low"
    
    @property
    def progress_color(self):
        pct = self.percentage_used

        if pct >= 100:
            return "bg-danger"      # Red
        elif pct >= 90:
            return "bg-warning"     # Yellow
        elif pct >= 75:
            return "bg-info"        # Blue
        else:
            return "bg-success"     # Green

