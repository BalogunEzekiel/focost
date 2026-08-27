from datetime import date, timedelta

from app.models.goal import Goal
from app.models.goal_contribution import GoalContribution


def make_goal():

    return Goal(
        user_id=1,
        title="Emergency Fund",
        goal_type="Savings",
        target_amount=1000000,
        target_date=date.today() + timedelta(days=180),
        priority="High",
        status="In Progress",
        reminder=True,
    )


def test_goal_without_contributions(app):

    with app.app_context():

        goal = make_goal()

        assert goal.saved_amount == 0
        assert goal.remaining_amount == 1000000
        assert goal.percentage_completed == 0
        assert goal.progress_percentage == 0
        assert goal.saved == 0
        assert goal.remaining == 1000000
        assert goal.target == 1000000


def test_goal_contribution_calculations(app):

    with app.app_context():

        goal = make_goal()

        contribution = GoalContribution(
            amount=250000,
        )

        goal.contributions.append(contribution)

        assert goal.saved_amount == 250000
        assert goal.remaining_amount == 750000
        assert goal.percentage_completed == 25
        assert goal.progress_percentage == 25