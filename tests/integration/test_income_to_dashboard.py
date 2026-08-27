from datetime import date

from app.extensions import db
from app.models.income import Income
from app.services.dashboard_service import DashboardService


def test_income_reaches_dashboard_service(
    app,
    user,
):

    with app.app_context():

        income = Income(
            user_id=user.id,
            source="Salary",
            category="Employment",
            amount=750000,
            received_date=date.today(),
        )

        db.session.add(income)
        db.session.commit()

        summary = DashboardService.build_summary(
            user.id
        )

        assert summary is not None