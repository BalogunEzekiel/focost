from datetime import date

from app.extensions import db
from app.models.expense import Expense
from app.services.dashboard_service import DashboardService


def test_expense_reaches_dashboard_service(
    app,
    user,
):

    with app.app_context():

        expense = Expense(
            user_id=user.id,
            category="Food",
            merchant="Restaurant",
            amount=25000,
            payment_method="Card",
            expense_date=date.today(),
        )

        db.session.add(expense)
        db.session.commit()

        summary = DashboardService.build_summary(
            user.id
        )

        assert summary is not None