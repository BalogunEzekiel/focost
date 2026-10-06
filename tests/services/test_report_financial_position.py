from datetime import date

from app.extensions import db
from app.models.asset import Asset
from app.models.expense import Expense
from app.models.goal import Goal
from app.models.goal_contribution import GoalContribution
from app.models.income import Income
from app.models.investment_event import InvestmentEvent
from app.reports.exports import ExportService
from app.reports.services import ReportService
from app.services.dashboard_service import DashboardService


def test_financial_position_reconciles_cash_goals_and_investments(app, user):
    with app.app_context():
        today = date.today()

        db.session.add(
            Income(
                user_id=user.id,
                source="Salary",
                category="Salary",
                amount=10000,
                received_date=today,
            )
        )

        goal = Goal(
            user_id=user.id,
            title="Emergency Fund",
            goal_type="Savings",
            target_amount=3000,
            target_date=today,
        )
        db.session.add(goal)
        db.session.flush()

        goal_expense = Expense(
            user_id=user.id,
            category="Goal Contribution",
            merchant=goal.title,
            amount=2000,
            payment_method="Internal Transfer",
            expense_date=today,
            transaction_class="goal_contribution",
        )
        db.session.add(goal_expense)
        db.session.flush()
        db.session.add(
            GoalContribution(
                goal_id=goal.id,
                user_id=user.id,
                amount=2000,
                contribution_date=today,
                expense_id=goal_expense.id,
            )
        )

        investment_expense = Expense(
            user_id=user.id,
            category="Investment",
            merchant="Test Investment",
            amount=3000,
            payment_method="Internal Investment Funding",
            expense_date=today,
            transaction_class="investment",
        )
        db.session.add(investment_expense)
        db.session.flush()

        asset = Asset(
            user_id=user.id,
            name="Test Investment",
            asset_type="Investment",
            investment_type="Fund",
            acquisition_date=today,
            acquisition_cost=3000,
            cost_basis=3000,
            current_value=3500,
            currency="NGN",
            source_expense_id=investment_expense.id,
        )
        db.session.add(asset)
        db.session.flush()

        db.session.add(
            InvestmentEvent(
                asset_id=asset.id,
                user_id=user.id,
                event_type="valuation",
                event_date=today,
                amount=500,
                previous_value=3000,
                new_value=3500,
                realized_gain_loss=500,
            )
        )
        db.session.commit()

        position = DashboardService.financial_position_summary(user.id)

        assert position["cash_income"] == 10000
        assert position["cash_expenses"] == 5000
        assert position["available_balance"] == 5000
        assert position["goal_contributions"] == 2000
        assert position["investment_current_value"] == 3500
        assert position["net_worth"] == 10500

        report = ReportService.report_data(user.id)
        assert report["financial_position"] == position


def test_financial_position_does_not_double_count_goal_contribution_or_investment(app, user):
    with app.app_context():
        today = date.today()
        db.session.add(
            Income(
                user_id=user.id,
                source="Salary",
                category="Salary",
                amount=20000,
                received_date=today,
            )
        )
        db.session.commit()

        # Create a goal contribution and investment as actual cash outflows.
        goal = Goal(
            user_id=user.id,
            title="House Fund",
            goal_type="Savings",
            target_amount=5000,
            target_date=today,
        )
        db.session.add(goal)
        db.session.commit()

        goal_expense = Expense(
            user_id=user.id,
            category="Goal Contribution",
            merchant=goal.title,
            amount=5000,
            payment_method="Internal Transfer",
            expense_date=today,
            transaction_class="goal_contribution",
        )
        db.session.add(goal_expense)
        db.session.flush()
        db.session.add(
            GoalContribution(
                goal_id=goal.id,
                user_id=user.id,
                amount=5000,
                contribution_date=today,
                expense_id=goal_expense.id,
            )
        )

        investment_expense = Expense(
            user_id=user.id,
            category="Investment",
            merchant="Fund",
            amount=5000,
            payment_method="Internal Investment Funding",
            expense_date=today,
            transaction_class="investment",
        )
        db.session.add(investment_expense)
        db.session.flush()
        db.session.add(
            Asset(
                user_id=user.id,
                name="Fund",
                asset_type="Investment",
                investment_type="Fund",
                acquisition_date=today,
                acquisition_cost=5000,
                cost_basis=5000,
                current_value=5000,
                currency="NGN",
                source_expense_id=investment_expense.id,
            )
        )
        db.session.commit()

        position = DashboardService.financial_position_summary(user.id)

        # 20,000 cash income - 10,000 cash allocations = 10,000 available.
        # Add back the two designated stores of value exactly once.
        assert position["available_balance"] == 10000
        assert position["goal_contributions"] == 5000
        assert position["investment_current_value"] == 5000
        assert position["net_worth"] == 20000


def test_report_exports_include_financial_position(app, user):
    with app.app_context():
        today = date.today()
        db.session.add(
            Income(
                user_id=user.id,
                source="Salary",
                category="Salary",
                amount=1000,
                received_date=today,
            )
        )
        db.session.commit()

        data = ReportService.report_data(user.id)
        pdf = ExportService.pdf(data)
        excel = ExportService.excel(data)

        assert pdf.getvalue().startswith(b"%PDF")
        assert excel.getvalue().startswith(b"PK")