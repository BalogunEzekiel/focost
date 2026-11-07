from app.extensions import db

from app.models.goal import Goal
from app.models.goal_contribution import GoalContribution
from app.models.expense import Expense
from app.models.income import Income
from app.models.user import User
from app.models.notification import Notification
from datetime import datetime
from app.utils.timezone import today

class GoalService:


    @staticmethod
    def create_goal(form, user_id):
        user = db.session.get(User, user_id)
        goal = Goal(
            user_id=user_id,
            currency=(user.base_currency if user else "NGN") or "NGN",
            title=form.title.data,
            goal_type=form.goal_type.data,
            target_amount=float(form.target_amount.data),
            target_date=form.target_date.data,
            priority=form.priority.data,
            notes=form.notes.data,
            status="In Progress",
        )

        db.session.add(goal)
        db.session.commit()

        return goal

    @staticmethod
    def update_goal(goal, form):
        goal.title = form.title.data
        goal.goal_type = form.goal_type.data
        new_target = float(form.target_amount.data)

        if new_target <= 0:
            raise ValueError("Goal target amount must be greater than zero.")

        if new_target + 1e-9 < float(goal.saved_amount or 0):
            raise ValueError(
                f"Goal target cannot be reduced below the amount already contributed "
                f"({goal.saved_amount:,.2f})."
            )

        goal.target_amount = new_target
        goal.target_date = form.target_date.data
        goal.priority = form.priority.data
        goal.notes = form.notes.data

        db.session.commit()

        return goal

    @staticmethod
    def delete_goal(goal):
        """
        Terminate a goal and return every contribution made to it as cash income.

        Goal contributions were real cash outflows when they were made, so
        their original Goal Contribution Expense records are historical
        financial transactions and MUST NEVER be deleted or reversed.

        When the goal is terminated, the total contributed amount is recorded
        as a NEW income transaction dated on the actual termination date.
        This makes the returned cash flow through FOCOST's normal income
        source of truth and therefore automatically affects savings, available
        balance, cashflow, charts, reports and other income-based analysis.

        The goal and its GoalContribution history are deleted. The linked
        Expense records remain permanently in the expense ledger.
        """
        if not goal or not goal.id:
            return 0.0

        contributions = list(goal.contributions or [])
        total_return = sum(
            float(contribution.amount or 0)
            for contribution in contributions
        )

        # IMPORTANT: NEVER delete or reverse the original Goal Contribution
        # expenses.  They are real historical cash-outflow transactions and
        # must remain permanently recorded in the expense ledger.
        #
        # GoalContribution.expense_id is defined with ON DELETE SET NULL, so
        # when the contribution records are deleted with the goal, the linked
        # Expense records remain intact and their foreign-key link is cleared
        # by the database.

        # Remove goal-related notifications so deleted goal history does not
        # continue appearing in the notification centre.
        if goal.id:
            goal_notification_prefixes = (
                f"GOAL_COMPLETED_{goal.id}",
                f"GOAL_DUE_{goal.id}",
                f"GOAL_BEHIND_{goal.id}",
            )
            Notification.query.filter(
                Notification.user_id == goal.user_id,
                Notification.unique_key.in_(goal_notification_prefixes),
            ).delete(synchronize_session=False)

        # Restore the contributed cash at the moment of termination.  A goal
        # with no contributions simply disappears without creating income.
        if total_return > 0:
            termination_date = today()
            db.session.add(
                Income(
                    user_id=goal.user_id,
                    source=goal.title,
                    category="Goal Termination Return",
                    amount=total_return,
                    currency=goal.currency or "NGN",
                    received_date=termination_date,
                    notes=(
                        f"Returned contributions from terminated goal: "
                        f"{goal.title}"
                    ),
                    recurring=False,
                    transaction_class="goal_termination",
                )
            )

        db.session.delete(goal)
        db.session.commit()

        return total_return

    @staticmethod
    def add_contribution(form, goal, user_id):
        from app.subscriptions.service import SubscriptionService
        from app.services.dashboard_service import DashboardService

        amount = float(form.amount.data or 0)

        if amount <= 0:
            raise ValueError("Contribution must be greater than zero.")

        contribution_date = form.contribution_date.data

        if goal.user_id != user_id:
            raise ValueError("You are not authorized to contribute to this goal.")

        remaining = float(goal.remaining_amount or 0)

        if remaining <= 0 or goal.progress_percentage >= 100:
            raise ValueError(
                "This goal has already been achieved. Additional contributions "
                "are not permitted."
            )

        if amount > remaining + 1e-9:
            from app.services.currency_service import CurrencyService
            remaining_text = CurrencyService.format(remaining, goal.currency or "NGN", include_code=True)
            raise ValueError(
                f"Contribution cannot exceed the remaining goal amount of {remaining_text}."
            )

        allowed, message = SubscriptionService.can_add_transaction(user_id)

        if not allowed:
            raise ValueError(message)

        available_cash = DashboardService.available_balance(
            user_id,
            as_of=contribution_date,
        )
        from app.services.financial_currency_service import FinancialCurrencyService
        display_currency = FinancialCurrencyService.display_currency(user_id)
        contribution_in_display_currency = FinancialCurrencyService.convert_value(
            amount, goal.currency or "NGN", display_currency, on_date=contribution_date
        )

        if contribution_in_display_currency > available_cash + 1e-9:
            from app.services.currency_service import CurrencyService
            available_text = CurrencyService.format(available_cash, display_currency, include_code=True)
            raise ValueError(
                f"Insufficient available balance. Available balance is {available_text}."
            )

        expense = Expense(
            user_id=user_id,
            category="Goal Contribution",
            merchant=goal.title,
            description=f"Contribution to goal: {goal.title}",
            amount=amount,
            currency=goal.currency or "NGN",
            payment_method="Internal Transfer",
            expense_date=contribution_date,
            notes=form.note.data,
            recurring=False,
            transaction_class="goal_contribution",
        )

        db.session.add(expense)
        db.session.flush()

        contribution = GoalContribution(
            goal_id=goal.id,
            user_id=user_id,
            amount=amount,
            currency=goal.currency or "NGN",
            contribution_date=contribution_date,
            note=form.note.data,
            expense_id=expense.id,
        )

        db.session.add(contribution)
        db.session.commit()

        return contribution

    @staticmethod
    def update_contribution(contribution, form, user_id):
        from app.services.dashboard_service import DashboardService

        goal = contribution.goal
        new_amount = float(form.amount.data or 0)

        if new_amount <= 0:
            raise ValueError("Contribution must be greater than zero.")

        other_saved = sum(
            float(c.amount or 0)
            for c in goal.contributions
            if c.is_active and c.id != contribution.id
        )

        remaining_after_others = max(
            float(goal.target_amount or 0) - other_saved,
            0,
        )

        if new_amount > remaining_after_others + 1e-9:
            from app.services.currency_service import CurrencyService
            remaining_text = CurrencyService.format(remaining_after_others, goal.currency or "NGN", include_code=True)
            raise ValueError(
                f"Contribution cannot exceed the remaining goal amount of {remaining_text}."
            )

        linked_expense = contribution.expense
        exclude_id = linked_expense.id if linked_expense else None

        available_cash = DashboardService.available_balance(
            user_id,
            exclude_expense_id=exclude_id,
            as_of=form.contribution_date.data,
        )
        from app.services.financial_currency_service import FinancialCurrencyService
        display_currency = FinancialCurrencyService.display_currency(user_id)
        contribution_in_display_currency = FinancialCurrencyService.convert_value(
            new_amount, goal.currency or "NGN", display_currency,
            on_date=form.contribution_date.data,
        )

        if contribution_in_display_currency > available_cash + 1e-9:
            from app.services.currency_service import CurrencyService
            available_text = CurrencyService.format(available_cash, display_currency, include_code=True)
            raise ValueError(
                f"Insufficient available balance. Available balance is {available_text}."
            )

        contribution.amount = new_amount
        contribution.contribution_date = form.contribution_date.data
        contribution.note = form.note.data

        if linked_expense:
            linked_expense.amount = new_amount
            linked_expense.expense_date = form.contribution_date.data
            linked_expense.notes = form.note.data
            linked_expense.transaction_class = "goal_contribution"

        db.session.commit()

        return contribution

    @staticmethod
    def get_goal_statistics(user_id):
        goals = Goal.query.filter_by(
            user_id=user_id
        ).all()

        total_goals = len(goals)

        completed = 0
        overdue = 0
        in_progress = 0

        total_target = 0
        total_saved = 0

        from app.services.financial_currency_service import FinancialCurrencyService
        display_currency = FinancialCurrencyService.display_currency(user_id)
        from app.utils.timezone import today
        for goal in goals:
            total_target += FinancialCurrencyService.convert_value(
                goal.target_amount, goal.currency or "NGN", display_currency, on_date=today()
            )
            total_saved += FinancialCurrencyService.convert_value(
                goal.saved_amount, goal.currency or "NGN", display_currency, on_date=today()
            )

            if goal.progress_status == "Completed":
                completed += 1
            elif goal.progress_status == "Overdue":
                overdue += 1
            else:
                in_progress += 1

        return {
            "total_goals": total_goals,
            "completed": completed,
            "overdue": overdue,
            "in_progress": in_progress,
            "total_target": total_target,
            "total_saved": total_saved,
            "remaining": total_target - total_saved,
        }