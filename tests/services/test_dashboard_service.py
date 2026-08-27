from datetime import date

from app.extensions import db
from app.models.income import Income
from app.models.expense import Expense
from app.services.dashboard_service import DashboardService


def test_dashboard_period_dates():

    start, end = DashboardService.get_period_dates(
        "month"
    )

    assert start is not None
    assert end is not None
    assert start <= end


def test_dashboard_summary_with_no_transactions(app, user):

    with app.app_context():

        result = DashboardService.build_summary(
            user.id
        )

        assert result is not None


def test_dashboard_with_financial_data(app, user):

    with app.app_context():

        db.session.add(
            Income(
                user_id=user.id,
                source="Salary",
                category="Employment",
                amount=500000,
                received_date=date.today(),
            )
        )

        db.session.add(
            Expense(
                user_id=user.id,
                category="Food",
                merchant="Restaurant",
                amount=100000,
                payment_method="Card",
                expense_date=date.today(),
            )
        )

        db.session.commit()

        result = DashboardService.build_summary(
            user.id
        )

        assert result is not None