####################################################################################################
# FILE: app/models/goal.py
####################################################################################################

from app.extensions import db
from app.models.base import BaseModel
from app.utils.timezone import today


class Goal(BaseModel):
    __tablename__ = "goals"

    __table_args__ = (
        db.CheckConstraint(
            "target_amount > 0",
            name="ck_goals_target_amount_positive",
        ),
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
    )

    title = db.Column(
        db.String(150),
        nullable=False,
    )

    goal_type = db.Column(
        db.String(100),
        nullable=False,
    )

    target_amount = db.Column(
        db.Float,
        nullable=False,
    )

    target_date = db.Column(
        db.Date,
        nullable=False,
    )

    priority = db.Column(
        db.String(20),
        default="Medium",
    )

    status = db.Column(
        db.String(20),
        default="In Progress",
    )

    notes = db.Column(
        db.Text,
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "goals",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    contributions = db.relationship(
        "GoalContribution",
        backref="goal",
        lazy=True,
        cascade="all, delete-orphan",
    )

    completed_at = db.Column(
        db.DateTime,
    )

    reminder = db.Column(
        db.Boolean,
        default=True,
    )

    @property
    def saved_amount(self):
        """
        Return the cumulative value of all contributions currently
        associated with this goal.

        The calculation intentionally uses the relationship collection
        directly so that it works consistently for both persisted
        contributions loaded from the database and contributions that
        have been attached to a transient Goal instance but have not
        yet been committed.

        The result is capped at the goal target amount so that the
        displayed/progress value cannot exceed the stated goal target.
        """

        target_amount = float(self.target_amount or 0)

        contribution_total = sum(
            float(contribution.amount or 0)
            for contribution in self.contributions
            if contribution.amount is not None
        )

        return min(
            target_amount,
            contribution_total,
        )

    @property
    def remaining_amount(self):
        """
        Return the remaining amount required to reach the goal target.
        """

        return max(
            float(self.target_amount or 0) - self.saved_amount,
            0,
        )

    @property
    def percentage_completed(self):
        """
        Return the percentage of the goal target that has been saved.
        """

        target_amount = float(self.target_amount or 0)

        if target_amount <= 0:
            return 0

        return round(
            (self.saved_amount / target_amount) * 100,
            2,
        )

    @property
    def progress_status(self):
        """
        Return the current progress status of the goal.
        """

        if self.percentage_completed >= 100:
            return "Completed"

        today_date = today()

        if self.target_date < today_date:
            return "Overdue"

        if self.percentage_completed >= 75:
            return "On Track"

        if self.percentage_completed >= 40:
            return "At Risk"

        if self.target_date > today_date:
            return "In Progress"

        return "Behind"

    @property
    def progress_percentage(self):
        """
        Return the goal completion percentage capped at 100%.
        """

        target_amount = float(self.target_amount or 0)

        if target_amount <= 0:
            return 0

        percentage = (
            self.saved_amount / target_amount
        ) * 100

        return round(
            min(percentage, 100),
            2,
        )

    @property
    def days_remaining(self):
        """
        Return the number of days remaining until the target date.
        """

        if self.percentage_completed >= 100:
            return 0

        return (
            self.target_date - today()
        ).days

    @property
    def monthly_contribution(self):
        """
        Return the estimated monthly contribution required to
        reach the remaining goal amount.
        """

        if self.days_remaining <= 0:
            return self.remaining_amount

        months = max(
            self.days_remaining / 30,
            1,
        )

        return round(
            self.remaining_amount / months,
            2,
        )


    @property
    def progress_color(self):
        """Bootstrap progress colour shared by goal pages and dashboard."""
        status = self.progress_status
        return {
            "Completed": "bg-success",
            "Overdue": "bg-danger",
            "On Track": "bg-primary",
            "At Risk": "bg-warning",
            "Behind": "bg-danger",
            "In Progress": "bg-secondary",
        }.get(status, "bg-secondary")

    @property
    def badge_class(self):
        """Badge colour using the same goal status theme everywhere."""
        status = self.progress_status
        return {
            "Completed": "bg-success",
            "Overdue": "bg-danger",
            "On Track": "bg-primary",
            "At Risk": "bg-warning text-dark",
            "Behind": "bg-danger",
            "In Progress": "bg-secondary",
        }.get(status, "bg-secondary")

    @property
    def background_class(self):
        """Light background tint matching the goal status theme."""
        status = self.progress_status
        return {
            "Completed": "bg-success-subtle",
            "Overdue": "bg-danger-subtle",
            "On Track": "bg-primary-subtle",
            "At Risk": "bg-warning-subtle",
            "Behind": "bg-danger-subtle",
            "In Progress": "bg-light",
        }.get(status, "bg-light")

    @property
    def percentage(self):
        """
        Backward-compatible alias for progress_percentage.
        """

        return self.progress_percentage

    @property
    def saved(self):
        """
        Backward-compatible alias for saved_amount.
        """

        return self.saved_amount

    @property
    def remaining(self):
        """
        Backward-compatible alias for remaining_amount.
        """

        return self.remaining_amount

    @property
    def target(self):
        """
        Backward-compatible alias for target_amount.
        """

        return self.target_amount