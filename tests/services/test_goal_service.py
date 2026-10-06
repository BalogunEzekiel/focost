####################################################################################################
# FILE: tests/services/test_goal_service.py
####################################################################################################

from datetime import date, timedelta

from app.extensions import db
from app.models.expense import Expense
from app.models.goal import Goal
from app.models.goal_contribution import GoalContribution
from app.models.income import Income
from app.services.goal_service import GoalService


def test_delete_goal_returns_contributions_as_income_and_removes_history(app, user):
    with app.app_context():
        goal = Goal(
            user_id=user.id,
            title="Weekend Getaway",
            goal_type="Travel",
            target_amount=100000,
            target_date=date.today() + timedelta(days=90),
            priority="Medium",
            status="In Progress",
        )
        db.session.add(goal)
        db.session.flush()

        expense = Expense(
            user_id=user.id,
            category="Goal Contribution",
            merchant=goal.title,
            description=f"Contribution to goal: {goal.title}",
            amount=25000,
            payment_method="Internal Transfer",
            expense_date=date.today(),
            transaction_class="goal_contribution",
        )
        db.session.add(expense)
        db.session.flush()

        contribution = GoalContribution(
            goal_id=goal.id,
            user_id=user.id,
            amount=25000,
            contribution_date=date.today(),
            expense_id=expense.id,
        )
        db.session.add(contribution)
        db.session.commit()

        goal_id = goal.id
        returned = GoalService.delete_goal(goal)

        assert returned == 25000
        assert Goal.query.filter_by(id=goal_id).first() is None
        assert GoalContribution.query.filter_by(goal_id=goal_id).count() == 0
        preserved_expense = Expense.query.filter_by(id=expense.id).first()
        assert preserved_expense is not None
        assert preserved_expense.amount == 25000
        assert preserved_expense.category == "Goal Contribution"

        income = Income.query.filter_by(
            user_id=user.id,
            category="Goal Termination Return",
        ).first()
        assert income is not None
        assert income.amount == 25000
        assert income.received_date == date.today()


def test_delete_goal_preserves_every_original_contribution_expense(app, user):
    with app.app_context():
        goal = Goal(
            user_id=user.id,
            title="Emergency Goal",
            goal_type="Savings",
            target_amount=200000,
            target_date=date.today() + timedelta(days=90),
            status="In Progress",
        )
        db.session.add(goal)
        db.session.flush()

        expenses = []
        for amount in (30000, 45000, 25000):
            expense = Expense(
                user_id=user.id,
                category="Goal Contribution",
                merchant=goal.title,
                description=f"Contribution to goal: {goal.title}",
                amount=amount,
                payment_method="Internal Transfer",
                expense_date=date.today(),
                transaction_class="goal_contribution",
            )
            db.session.add(expense)
            db.session.flush()
            expenses.append(expense)

            db.session.add(GoalContribution(
                goal_id=goal.id,
                user_id=user.id,
                amount=amount,
                contribution_date=date.today(),
                expense_id=expense.id,
            ))

        db.session.commit()

        goal_id = goal.id
        expense_ids = [expense.id for expense in expenses]

        returned = GoalService.delete_goal(goal)

        assert returned == 100000
        assert Goal.query.filter_by(id=goal_id).first() is None
        assert GoalContribution.query.filter_by(goal_id=goal_id).count() == 0

        preserved_expenses = Expense.query.filter(
            Expense.id.in_(expense_ids)
        ).order_by(Expense.id).all()

        assert len(preserved_expenses) == 3
        assert [expense.amount for expense in preserved_expenses] == [
            30000, 45000, 25000
        ]
        assert all(
            expense.category == "Goal Contribution"
            for expense in preserved_expenses
        )

        returned_income = Income.query.filter_by(
            user_id=user.id,
            category="Goal Termination Return",
        ).first()
        assert returned_income is not None
        assert returned_income.amount == 100000
        assert returned_income.received_date == date.today()


def test_delete_goal_without_contributions_creates_no_income(app, user):
    with app.app_context():
        goal = Goal(
            user_id=user.id,
            title="Empty Goal",
            goal_type="Savings",
            target_amount=100000,
            target_date=date.today() + timedelta(days=90),
            status="In Progress",
        )
        db.session.add(goal)
        db.session.commit()

        GoalService.delete_goal(goal)

        assert Income.query.filter_by(
            user_id=user.id,
            category="Goal Termination Return",
        ).count() == 0
