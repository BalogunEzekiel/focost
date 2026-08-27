from datetime import date, timedelta

from app.models.budget import Budget


def make_budget(**overrides):

    data = {
        "user_id": 1,
        "category": "Food",
        "amount": 100000,
        "period": "Monthly",
        "start_date": date.today(),
        "end_date": date.today() + timedelta(days=30),
        "spent": 50000,
    }

    data.update(overrides)

    return Budget(**data)


def test_budget_remaining(app):

    with app.app_context():

        budget = make_budget(
            amount=100000,
            spent=40000,
        )

        assert budget.remaining == 60000


def test_budget_percentage_used(app):

    with app.app_context():

        budget = make_budget(
            amount=100000,
            spent=50000,
        )

        assert budget.percentage_used == 50


def test_budget_status_healthy(app):

    with app.app_context():

        budget = make_budget(
            amount=100000,
            spent=50000,
        )

        assert budget.status == "Healthy"
        assert budget.risk == "Low"
        assert budget.progress_color == "bg-success"


def test_budget_status_warning(app):

    with app.app_context():

        budget = make_budget(
            amount=100000,
            spent=80000,
        )

        assert budget.status == "Warning"
        assert budget.risk == "Medium"


def test_budget_status_critical(app):

    with app.app_context():

        budget = make_budget(
            amount=100000,
            spent=95000,
        )

        assert budget.status == "Critical"
        assert budget.risk == "High"


def test_budget_status_exceeded(app):

    with app.app_context():

        budget = make_budget(
            amount=100000,
            spent=120000,
        )

        assert budget.status == "Exceeded"
        assert budget.risk == "Critical"
        assert budget.remaining == 0