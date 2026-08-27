from datetime import date

from app.models.income import Income


def test_income_model(app):

    with app.app_context():

        income = Income(
            user_id=1,
            source="Salary",
            category="Employment",
            amount=500000,
            received_date=date.today(),
            notes="Monthly salary",
            recurring=True,
        )

        assert income.source == "Salary"
        assert income.category == "Employment"
        assert income.amount == 500000
        assert income.received_date == date.today()
        assert income.recurring is True


def test_income_representation(app):

    with app.app_context():

        income = Income(
            user_id=1,
            source="Salary",
            category="Employment",
            amount=500000,
            received_date=date.today(),
        )

        assert "Salary" in repr(income)
        assert "500000" in repr(income)