import pytest
from datetime import date

from app.extensions import db
from app.models.user import User
from app.models.income import Income
from app.models.expense import Expense
from app.reports.services import ReportService


# ============================================================
# HELPERS
# ============================================================

def create_user():
    user = User(
        first_name="Test",
        last_name="User",
        email="report-test@example.com",
        currency="NGN",
    )
    user.set_password("TestPassword123!")
    db.session.add(user)
    db.session.commit()
    return user


def create_income(
    user_id,
    source,
    category,
    amount,
    received_date,
):
    income = Income(
        user_id=user_id,
        source=source,
        category=category,
        amount=amount,
        received_date=received_date,
    )
    db.session.add(income)
    return income


def create_expense(
    user_id,
    category,
    merchant,
    amount,
    expense_date,
    payment_method="Cash",
):
    expense = Expense(
        user_id=user_id,
        category=category,
        merchant=merchant,
        amount=amount,
        expense_date=expense_date,
        payment_method=payment_method,
    )
    db.session.add(expense)
    return expense


# ============================================================
# DATE PARSING
# ============================================================

def test_date_helper_accepts_none():
    assert ReportService._date(None) is None


def test_date_helper_accepts_date():
    value = date(2026, 8, 15)

    result = ReportService._date(value)

    assert result == value


def test_date_helper_accepts_datetime():
    from datetime import datetime

    value = datetime(2026, 8, 15, 10, 30)

    result = ReportService._date(value)

    assert result == value


def test_date_helper_parses_string():
    result = ReportService._date("2026-08-15")

    assert result == date(2026, 8, 15)


def test_date_helper_rejects_invalid_string():
    with pytest.raises(ValueError):
        ReportService._date("15-08-2026")


# ============================================================
# CATEGORY DISCOVERY
# ============================================================

def test_categories_returns_unique_sorted_categories(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "Salary",
            "Salary",
            500000,
            date(2026, 8, 1),
        )

        create_income(
            user.id,
            "Freelance",
            "Freelance",
            100000,
            date(2026, 8, 5),
        )

        create_expense(
            user.id,
            "Food",
            "Restaurant",
            20000,
            date(2026, 8, 6),
        )

        create_expense(
            user.id,
            "Salary",
            "Something",
            5000,
            date(2026, 8, 7),
        )

        db.session.commit()

        result = ReportService.categories(user.id)

        assert result == [
            "Food",
            "Freelance",
            "Salary",
        ]


def test_categories_returns_empty_list_for_user_without_transactions(app):
    with app.app_context():

        user = create_user()

        result = ReportService.categories(user.id)

        assert result == []


# ============================================================
# FILTERED INCOME QUERY
# ============================================================

def test_income_query_filters_by_user(app):
    with app.app_context():

        user = create_user()
        other_user = User(
            first_name="Other",
            last_name="User",
            email="other-report@example.com",
            currency="NGN",
        )
        other_user.set_password("TestPassword123!")

        db.session.add(other_user)
        db.session.commit()

        create_income(
            user.id,
            "Salary",
            "Salary",
            500000,
            date(2026, 8, 1),
        )

        create_income(
            other_user.id,
            "Salary",
            "Salary",
            900000,
            date(2026, 8, 1),
        )

        db.session.commit()

        result = ReportService._income_query(user.id).all()

        assert len(result) == 1
        assert result[0].amount == 500000


def test_income_query_filters_by_date(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "January Income",
            "Salary",
            100000,
            date(2026, 1, 10),
        )

        create_income(
            user.id,
            "August Income",
            "Salary",
            500000,
            date(2026, 8, 10),
        )

        db.session.commit()

        result = ReportService._income_query(
            user.id,
            "2026-08-01",
            "2026-08-31",
        ).all()

        assert len(result) == 1
        assert result[0].amount == 500000


def test_income_query_filters_by_category(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "Salary",
            "Salary",
            500000,
            date(2026, 8, 1),
        )

        create_income(
            user.id,
            "Freelance",
            "Freelance",
            200000,
            date(2026, 8, 2),
        )

        db.session.commit()

        result = ReportService._income_query(
            user.id,
            category="Salary",
        ).all()

        assert len(result) == 1
        assert result[0].category == "Salary"


# ============================================================
# FILTERED EXPENSE QUERY
# ============================================================

def test_expense_query_filters_by_date(app):
    with app.app_context():

        user = create_user()

        create_expense(
            user.id,
            "Food",
            "Restaurant",
            20000,
            date(2026, 7, 10),
        )

        create_expense(
            user.id,
            "Food",
            "Restaurant",
            30000,
            date(2026, 8, 10),
        )

        db.session.commit()

        result = ReportService._expense_query(
            user.id,
            "2026-08-01",
            "2026-08-31",
        ).all()

        assert len(result) == 1
        assert result[0].amount == 30000


def test_expense_query_filters_by_category(app):
    with app.app_context():

        user = create_user()

        create_expense(
            user.id,
            "Food",
            "Restaurant",
            20000,
            date(2026, 8, 1),
        )

        create_expense(
            user.id,
            "Transport",
            "Uber",
            15000,
            date(2026, 8, 2),
        )

        db.session.commit()

        result = ReportService._expense_query(
            user.id,
            category="Food",
        ).all()

        assert len(result) == 1
        assert result[0].category == "Food"


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

def test_dashboard_calculates_totals(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "Salary",
            "Salary",
            500000,
            date(2026, 8, 1),
        )

        create_income(
            user.id,
            "Freelance",
            "Freelance",
            100000,
            date(2026, 8, 5),
        )

        create_expense(
            user.id,
            "Food",
            "Restaurant",
            50000,
            date(2026, 8, 6),
        )

        create_expense(
            user.id,
            "Transport",
            "Uber",
            50000,
            date(2026, 8, 7),
        )

        db.session.commit()

        result = ReportService.dashboard(user.id)

        assert result["income"] == 600000
        assert result["expenses"] == 100000
        assert result["savings"] == 500000
        assert result["transactions"] == 4
        assert result["income_transactions"] == 2
        assert result["expense_transactions"] == 2


def test_dashboard_calculates_savings_rate(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "Salary",
            "Salary",
            500000,
            date(2026, 8, 1),
        )

        create_expense(
            user.id,
            "Food",
            "Food",
            100000,
            date(2026, 8, 2),
        )

        db.session.commit()

        result = ReportService.dashboard(user.id)

        assert result["savings"] == 400000
        assert result["savings_rate"] == pytest.approx(80.0)
        assert result["savings_progress"] == pytest.approx(80.0)


def test_dashboard_handles_zero_income(app):
    with app.app_context():

        user = create_user()

        create_expense(
            user.id,
            "Food",
            "Restaurant",
            50000,
            date(2026, 8, 1),
        )

        db.session.commit()

        result = ReportService.dashboard(user.id)

        assert result["income"] == 0
        assert result["expenses"] == 50000
        assert result["savings"] == -50000
        assert result["savings_rate"] == 0
        assert result["savings_progress"] == 0


def test_dashboard_category_filter(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "Salary",
            "Salary",
            500000,
            date(2026, 8, 1),
        )

        create_income(
            user.id,
            "Freelance",
            "Freelance",
            200000,
            date(2026, 8, 2),
        )

        create_expense(
            user.id,
            "Salary",
            "Salary Related",
            50000,
            date(2026, 8, 3),
        )

        create_expense(
            user.id,
            "Food",
            "Restaurant",
            30000,
            date(2026, 8, 4),
        )

        db.session.commit()

        result = ReportService.dashboard(
            user.id,
            category="Salary",
        )

        assert result["income"] == 500000
        assert result["expenses"] == 50000
        assert result["savings"] == 450000
        assert result["transactions"] == 2


def test_dashboard_date_filter(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "July Salary",
            "Salary",
            300000,
            date(2026, 7, 1),
        )

        create_income(
            user.id,
            "August Salary",
            "Salary",
            500000,
            date(2026, 8, 1),
        )

        create_expense(
            user.id,
            "July Food",
            "Food",
            50000,
            date(2026, 7, 5),
        )

        create_expense(
            user.id,
            "August Food",
            "Food",
            80000,
            date(2026, 8, 5),
        )

        db.session.commit()

        result = ReportService.dashboard(
            user.id,
            start_date="2026-08-01",
            end_date="2026-08-31",
        )

        assert result["income"] == 500000
        assert result["expenses"] == 80000
        assert result["savings"] == 420000


# ============================================================
# INCOME BY CATEGORY
# ============================================================

def test_income_by_category(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "Salary 1",
            "Salary",
            500000,
            date(2026, 8, 1),
        )

        create_income(
            user.id,
            "Salary 2",
            "Salary",
            200000,
            date(2026, 8, 2),
        )

        create_income(
            user.id,
            "Freelance",
            "Freelance",
            100000,
            date(2026, 8, 3),
        )

        db.session.commit()

        result = ReportService.income_by_category(user.id)

        assert result["labels"] == [
            "Salary",
            "Freelance",
        ]

        assert result["values"] == [
            700000.0,
            100000.0,
        ]


def test_income_by_category_respects_filter(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "Salary",
            "Salary",
            500000,
            date(2026, 8, 1),
        )

        create_income(
            user.id,
            "Freelance",
            "Freelance",
            100000,
            date(2026, 8, 2),
        )

        db.session.commit()

        result = ReportService.income_by_category(
            user.id,
            category="Salary",
        )

        assert result["labels"] == ["Salary"]
        assert result["values"] == [500000.0]


# ============================================================
# EXPENSE BY CATEGORY
# ============================================================

def test_expense_by_category(app):
    with app.app_context():

        user = create_user()

        create_expense(
            user.id,
            "Food",
            "Restaurant",
            50000,
            date(2026, 8, 1),
        )

        create_expense(
            user.id,
            "Food",
            "Supermarket",
            30000,
            date(2026, 8, 2),
        )

        create_expense(
            user.id,
            "Transport",
            "Uber",
            20000,
            date(2026, 8, 3),
        )

        db.session.commit()

        result = ReportService.expense_by_category(user.id)

        assert result["labels"] == [
            "Food",
            "Transport",
        ]

        assert result["values"] == [
            80000.0,
            20000.0,
        ]


def test_expense_by_category_respects_filter(app):
    with app.app_context():

        user = create_user()

        create_expense(
            user.id,
            "Food",
            "Restaurant",
            50000,
            date(2026, 8, 1),
        )

        create_expense(
            user.id,
            "Transport",
            "Uber",
            20000,
            date(2026, 8, 2),
        )

        db.session.commit()

        result = ReportService.expense_by_category(
            user.id,
            category="Food",
        )

        assert result["labels"] == ["Food"]
        assert result["values"] == [50000.0]


# ============================================================
# MONTHLY TREND
# ============================================================

def test_monthly_trend_returns_twelve_months_for_single_year(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "January Salary",
            "Salary",
            100000,
            date(2026, 1, 10),
        )

        create_income(
            user.id,
            "August Salary",
            "Salary",
            500000,
            date(2026, 8, 10),
        )

        create_expense(
            user.id,
            "January Food",
            "Food",
            20000,
            date(2026, 1, 15),
        )

        create_expense(
            user.id,
            "August Food",
            "Food",
            50000,
            date(2026, 8, 15),
        )

        db.session.commit()

        result = ReportService.monthly_trend(
            user.id,
            "2026-01-01",
            "2026-12-31",
        )

        assert len(result["labels"]) == 12
        assert len(result["income"]) == 12
        assert len(result["expenses"]) == 12

        assert result["income"][0] == 100000
        assert result["income"][7] == 500000

        assert result["expenses"][0] == 20000
        assert result["expenses"][7] == 50000


def test_monthly_trend_respects_category_filter(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "Salary",
            "Salary",
            500000,
            date(2026, 8, 1),
        )

        create_income(
            user.id,
            "Freelance",
            "Freelance",
            200000,
            date(2026, 8, 2),
        )

        create_expense(
            user.id,
            "Food",
            "Restaurant",
            50000,
            date(2026, 8, 3),
        )

        create_expense(
            user.id,
            "Salary",
            "Salary Related",
            30000,
            date(2026, 8, 4),
        )

        db.session.commit()

        result = ReportService.monthly_trend(
            user.id,
            "2026-01-01",
            "2026-12-31",
            "Salary",
        )

        assert result["income"][7] == 500000
        assert result["expenses"][7] == 30000


def test_monthly_trend_handles_multi_year_period(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "December Income",
            "Salary",
            100000,
            date(2025, 12, 10),
        )

        create_income(
            user.id,
            "January Income",
            "Salary",
            200000,
            date(2026, 1, 10),
        )

        create_expense(
            user.id,
            "December Expense",
            "Food",
            30000,
            date(2025, 12, 15),
        )

        create_expense(
            user.id,
            "January Expense",
            "Food",
            40000,
            date(2026, 1, 15),
        )

        db.session.commit()

        result = ReportService.monthly_trend(
            user.id,
            "2025-12-01",
            "2026-01-31",
        )

        assert result["labels"] == [
            "Dec 2025",
            "Jan 2026",
        ]

        assert result["income"] == [
            100000.0,
            200000.0,
        ]

        assert result["expenses"] == [
            30000.0,
            40000.0,
        ]


# ============================================================
# SUMMARY / REPORT DATA
# ============================================================

def test_get_summary_matches_dashboard(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "Salary",
            "Salary",
            500000,
            date(2026, 8, 1),
        )

        create_expense(
            user.id,
            "Food",
            "Restaurant",
            100000,
            date(2026, 8, 2),
        )

        db.session.commit()

        summary = ReportService.get_summary(
            user.id,
            "2026-08-01",
            "2026-08-31",
        )

        dashboard = ReportService.dashboard(
            user.id,
            "2026-08-01",
            "2026-08-31",
        )

        assert summary["income"] == dashboard["income"]
        assert summary["expenses"] == dashboard["expenses"]
        assert summary["savings"] == dashboard["savings"]


def test_report_data_contains_all_required_sections(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "Salary",
            "Salary",
            500000,
            date(2026, 8, 1),
        )

        create_expense(
            user.id,
            "Food",
            "Food",
            100000,
            date(2026, 8, 2),
        )

        db.session.commit()

        result = ReportService.report_data(
            user.id,
            "2026-08-01",
            "2026-08-31",
        )

        assert "summary" in result
        assert "income_categories" in result
        assert "expense_categories" in result
        assert "monthly_trend" in result


def test_report_data_respects_filters(app):
    with app.app_context():

        user = create_user()

        create_income(
            user.id,
            "Salary",
            "Salary",
            500000,
            date(2026, 8, 1),
        )

        create_income(
            user.id,
            "Freelance",
            "Freelance",
            200000,
            date(2026, 8, 2),
        )

        create_expense(
            user.id,
            "Salary",
            "Salary Expense",
            50000,
            date(2026, 8, 3),
        )

        create_expense(
            user.id,
            "Food",
            "Restaurant",
            100000,
            date(2026, 8, 4),
        )

        db.session.commit()

        result = ReportService.report_data(
            user.id,
            "2026-08-01",
            "2026-08-31",
            "Salary",
        )

        assert result["summary"]["income"] == 500000
        assert result["summary"]["expenses"] == 50000
        assert result["summary"]["savings"] == 450000

        assert result["income_categories"]["labels"] == [
            "Salary"
        ]

        assert result["expense_categories"]["labels"] == [
            "Salary"
        ]

        assert result["income_categories"]["values"] == [
            500000.0
        ]

        assert result["expense_categories"]["values"] == [
            50000.0
        ]