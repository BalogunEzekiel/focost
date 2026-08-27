from datetime import date, timedelta

from app.extensions import db
from app.models.budget import Budget
from app.services.dashboard_service import DashboardService


def test_budget_reaches_dashboard(
    app,
    user,
):

    with app.app_context():

        budget = Budget(
            user_id=user.id,
            category="Food",
            amount=100000,
            period="Monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            spent=50000,
        )

        db.session.add(budget)
        db.session.commit()

        data = DashboardService.get_dashboard_data(
            user.id
        )

        assert data is not None