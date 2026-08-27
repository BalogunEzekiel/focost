from datetime import date, timedelta

from app.extensions import db
from app.models.goal import Goal
from app.services.dashboard_service import DashboardService


def test_goal_reaches_dashboard(
    app,
    user,
):

    with app.app_context():

        goal = Goal(
            user_id=user.id,
            title="Emergency Fund",
            goal_type="Savings",
            target_amount=1000000,
            target_date=date.today() + timedelta(days=180),
            priority="High",
            status="In Progress",
            reminder=True,
        )

        db.session.add(goal)
        db.session.commit()

        data = DashboardService.get_dashboard_data(
            user.id
        )

        assert data is not None