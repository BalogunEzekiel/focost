from datetime import date

from app.models.expense import Expense


def test_expense_model(app):

    with app.app_context():

        expense = Expense(
            user_id=1,
            category="Food",
            merchant="Restaurant",
            description="Lunch",
            amount=15000,
            payment_method="Card",
            expense_date=date.today(),
            notes="Business lunch",
            recurring=False,
        )

        assert expense.category == "Food"
        assert expense.merchant == "Restaurant"
        assert expense.amount == 15000
        assert expense.payment_method == "Card"
        assert expense.recurring is False


def test_expense_representation(app):

    with app.app_context():

        expense = Expense(
            user_id=1,
            category="Food",
            merchant="Restaurant",
            amount=15000,
            payment_method="Card",
            expense_date=date.today(),
        )

        assert "Food" in repr(expense)
        assert "15000" in repr(expense)