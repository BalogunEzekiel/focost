from datetime import date, timedelta

from app.extensions import db
from app.models.asset import Asset
from app.models.expense import Expense
from app.models.goal import Goal
from app.models.goal_contribution import GoalContribution
from app.models.income import Income
from app.models.investment_event import InvestmentEvent
from app.services.dashboard_service import DashboardService
from app.services.goal_service import GoalService
from app.services.investment_service import InvestmentService


class DummyField:
    def __init__(self, value):
        self.data = value


class DummyContributionForm:
    def __init__(self, amount, contribution_date=None, note=""):
        self.amount = DummyField(amount)
        self.contribution_date = DummyField(contribution_date or date.today())
        self.note = DummyField(note)


def test_goal_contribution_cannot_exceed_target_or_balance(app, user, monkeypatch):
    with app.app_context():
        monkeypatch.setattr(
            "app.subscriptions.service.SubscriptionService.can_add_transaction",
            staticmethod(lambda user_id: (True, "")),
        )
        db.session.add(Income(user_id=user.id, source="Salary", category="Salary", amount=1000, received_date=date.today()))
        goal = Goal(user_id=user.id, title="Goal", goal_type="Savings", target_amount=500, target_date=date.today() + timedelta(days=30))
        db.session.add(goal)
        db.session.commit()

        GoalService.add_contribution(DummyContributionForm(500), goal, user.id)
        assert goal.saved_amount == 500
        assert Expense.query.filter_by(user_id=user.id, transaction_class="goal_contribution").count() == 1

        try:
            GoalService.add_contribution(DummyContributionForm(1), goal, user.id)
            assert False, "Completed goals must reject additional contributions"
        except ValueError as exc:
            assert "achieved" in str(exc).lower()


def test_goal_future_date_is_never_behind(app, user):
    with app.app_context():
        goal = Goal(
            user_id=user.id,
            title="Future Goal",
            goal_type="Savings",
            target_amount=1000,
            target_date=date.today() + timedelta(days=120),
        )
        db.session.add(goal)
        db.session.commit()
        item = next(x for x in DashboardService.build_goal_progress(user.id) if x["id"] == goal.id)
        assert item["status"] != "Behind"
        assert "behind schedule" not in item["recommendation"].lower()


def test_investment_funding_and_valuation_are_separate_from_operating_expense(app, user, monkeypatch):
    with app.app_context():
        monkeypatch.setattr(
            "app.subscriptions.service.SubscriptionService.can_add_transaction",
            staticmethod(lambda user_id: (True, "")),
        )
        db.session.add(Income(user_id=user.id, source="Salary", category="Salary", amount=5000, received_date=date.today()))
        db.session.commit()

        asset = InvestmentService.create(
            user,
            name="Test Investment",
            investment_type="Investment",
            acquisition_date=date.today(),
            amount=1000,
            current_value=1000,
        )
        assert asset.current_value == 1000
        assert Expense.query.filter_by(transaction_class="investment").one().amount == 1000
        assert DashboardService.available_balance(user.id) == 4000

        InvestmentService.update_valuation(user, asset, new_value=1200, event_date=date.today())
        assert asset.gain_loss == 200
        assert Income.query.filter_by(transaction_class="investment_gain").one().amount == 200
        # The valuation gain is non-cash and must not become spendable cash.
        assert DashboardService.available_balance(user.id) == 4000


def test_investment_full_liquidation_preserves_history(app, user, monkeypatch):
    with app.app_context():
        monkeypatch.setattr(
            "app.subscriptions.service.SubscriptionService.can_add_transaction",
            staticmethod(lambda user_id: (True, "")),
        )
        db.session.add(Income(user_id=user.id, source="Salary", category="Salary", amount=5000, received_date=date.today()))
        db.session.commit()
        asset = InvestmentService.create(
            user,
            name="Liquidation Test",
            investment_type="Investment",
            acquisition_date=date.today(),
            amount=1000,
            current_value=1000,
        )
        InvestmentService.liquidate(user, asset, amount=1000, liquidation_date=date.today())

        assert asset.is_active is False
        assert asset.current_value == 0
        assert InvestmentEvent.query.filter_by(asset_id=asset.id).count() >= 2
        assert Income.query.filter_by(transaction_class="investment_liquidation").one().amount == 1000
        assert DashboardService.available_balance(user.id) == 5000
