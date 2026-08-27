from datetime import date, datetime, timedelta

from sqlalchemy import and_
from sqlalchemy import extract
from sqlalchemy import func
from sqlalchemy import or_

from app.extensions import db

from app.models.income import Income
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.goal import Goal
from app.models.goal_contribution import GoalContribution


class FinanceQueries:
    """
    Central Financial Query Engine

    All AI modules obtain database information from this class.

    analytics.py
    forecasting.py
    advisor.py
    recommendation.py
    insights.py

    must NOT query the database directly.
    """

    # ==========================================================
    # DATE ENGINE
    # ==========================================================

    @staticmethod
    def get_period(period=None):
        """
        Returns (start_date, end_date)
        """

        today = date.today()

        if period is None:
            return None, None

        if period == "today":
            return today, today

        if period == "yesterday":

            d = today - timedelta(days=1)

            return d, d

        if period == "week":

            start = today - timedelta(days=today.weekday())

            return start, today

        if period == "last_week":

            end = today - timedelta(days=today.weekday() + 1)

            start = end - timedelta(days=6)

            return start, end

        if period == "month":

            start = today.replace(day=1)

            return start, today

        if period == "last_month":

            first_this_month = today.replace(day=1)

            end = first_this_month - timedelta(days=1)

            start = end.replace(day=1)

            return start, end

        if period == "year":

            start = date(today.year, 1, 1)

            return start, today

        return None, None

    # ==========================================================
    # INTERNAL FILTER
    # ==========================================================

    @staticmethod
    def apply_date_filter(query, model, field_name, period=None):

        start, end = FinanceQueries.get_period(period)

        if start is None:

            return query

        column = getattr(model, field_name)

        return query.filter(

            column >= start,

            column <= end

        )

    # ==========================================================
    # GENERIC SUM
    # ==========================================================

    @staticmethod
    def total(model, user_id, amount_field):

        return (

            db.session.query(

                func.coalesce(

                    func.sum(

                        getattr(model, amount_field)

                    ),

                    0

                )

            )

            .filter(

                model.user_id == user_id

            )

            .scalar()

        )
    
    # ==========================================================
    # INCOME ENGINE
    # ==========================================================

    @staticmethod
    def total_income(user_id, period=None):
        """
        Total income within a period.
        """

        query = (
            db.session.query(
                func.coalesce(
                    func.sum(Income.amount),
                    0
                )
            )
            .filter(
                Income.user_id == user_id
            )
        )

        query = FinanceQueries.apply_date_filter(
            query,
            Income,
            "received_date",
            period
        )

        return query.scalar()

    @staticmethod
    def income_by_category(
        user_id,
        category,
        period=None
    ):

        query = (
            db.session.query(
                func.coalesce(
                    func.sum(Income.amount),
                    0
                )
            )
            .filter(
                Income.user_id == user_id,
                Income.category == category
            )
        )

        query = FinanceQueries.apply_date_filter(
            query,
            Income,
            "received_date",
            period
        )

        return query.scalar()

    @staticmethod
    def income_by_source(
        user_id,
        source,
        period=None
    ):

        query = (
            db.session.query(
                func.coalesce(
                    func.sum(Income.amount),
                    0
                )
            )
            .filter(
                Income.user_id == user_id,
                Income.source.ilike(f"%{source}%")
            )
        )

        query = FinanceQueries.apply_date_filter(
            query,
            Income,
            "received_date",
            period
        )

        return query.scalar()

    @staticmethod
    def largest_income(user_id):

        return (
            Income.query
            .filter_by(
                user_id=user_id
            )
            .order_by(
                Income.amount.desc()
            )
            .first()
        )

    @staticmethod
    def average_income(
        user_id,
        period=None
    ):

        query = (
            db.session.query(
                func.coalesce(
                    func.avg(
                        Income.amount
                    ),
                    0
                )
            )
            .filter(
                Income.user_id == user_id
            )
        )

        query = FinanceQueries.apply_date_filter(
            query,
            Income,
            "received_date",
            period
        )

        return round(
            query.scalar() or 0,
            2
        )

    @staticmethod
    def income_count(
        user_id,
        period=None
    ):

        query = (
            Income.query.filter_by(
                user_id=user_id
            )
        )

        query = FinanceQueries.apply_date_filter(
            query,
            Income,
            "received_date",
            period
        )

        return query.count()

    @staticmethod
    def recurring_income(user_id):

        return (
            Income.query
            .filter(
                Income.user_id == user_id,
                Income.recurring.is_(True)
            )
            .all()
        )

    @staticmethod
    def income_sources(user_id):

        return (
            db.session.query(

                Income.source,

                func.sum(
                    Income.amount
                ).label("total")

            )

            .filter(
                Income.user_id == user_id
            )

            .group_by(
                Income.source
            )

            .order_by(
                func.sum(
                    Income.amount
                ).desc()
            )

            .all()
        )

    @staticmethod
    def income_categories(user_id):

        return (
            db.session.query(

                Income.category,

                func.sum(
                    Income.amount
                ).label("total")

            )

            .filter(
                Income.user_id == user_id
            )

            .group_by(
                Income.category
            )

            .order_by(
                func.sum(
                    Income.amount
                ).desc()
            )

            .all()
        )

    @staticmethod
    def latest_income(user_id):

        return (
            Income.query
            .filter_by(
                user_id=user_id
            )
            .order_by(
                Income.received_date.desc()
            )
            .first()
        )
    
    # ==========================================================
    # EXPENSE ENGINE
    # ==========================================================

    @staticmethod
    def total_expense(user_id, period=None):
        """
        Total expenses within a period.
        """

        query = (
            db.session.query(
                func.coalesce(
                    func.sum(Expense.amount),
                    0
                )
            )
            .filter(
                Expense.user_id == user_id
            )
        )

        query = FinanceQueries.apply_date_filter(
            query,
            Expense,
            "expense_date",
            period
        )

        return query.scalar()

    @staticmethod
    def expense_by_category(
        user_id,
        category,
        period=None
    ):

        query = (
            db.session.query(
                func.coalesce(
                    func.sum(Expense.amount),
                    0
                )
            )
            .filter(
                Expense.user_id == user_id,
                Expense.category == category
            )
        )

        query = FinanceQueries.apply_date_filter(
            query,
            Expense,
            "expense_date",
            period
        )

        return query.scalar()

    @staticmethod
    def expense_by_merchant(
        user_id,
        merchant,
        period=None
    ):

        query = (
            db.session.query(
                func.coalesce(
                    func.sum(Expense.amount),
                    0
                )
            )
            .filter(
                Expense.user_id == user_id,
                Expense.merchant.ilike(f"%{merchant}%")
            )
        )

        query = FinanceQueries.apply_date_filter(
            query,
            Expense,
            "expense_date",
            period
        )

        return query.scalar()

    @staticmethod
    def expense_by_payment_method(
        user_id,
        payment_method,
        period=None
    ):

        query = (
            db.session.query(
                func.coalesce(
                    func.sum(Expense.amount),
                    0
                )
            )
            .filter(
                Expense.user_id == user_id,
                Expense.payment_method == payment_method
            )
        )

        query = FinanceQueries.apply_date_filter(
            query,
            Expense,
            "expense_date",
            period
        )

        return query.scalar()

    @staticmethod
    def expense_by_description(
        user_id,
        keyword,
        period=None
    ):

        query = (
            db.session.query(
                func.coalesce(
                    func.sum(Expense.amount),
                    0
                )
            )
            .filter(
                Expense.user_id == user_id,
                Expense.description.ilike(f"%{keyword}%")
            )
        )

        query = FinanceQueries.apply_date_filter(
            query,
            Expense,
            "expense_date",
            period
        )

        return query.scalar()

    @staticmethod
    def average_expense(
        user_id,
        period=None
    ):

        query = (
            db.session.query(
                func.coalesce(
                    func.avg(
                        Expense.amount
                    ),
                    0
                )
            )
            .filter(
                Expense.user_id == user_id
            )
        )

        query = FinanceQueries.apply_date_filter(
            query,
            Expense,
            "expense_date",
            period
        )

        return round(
            query.scalar() or 0,
            2
        )

    @staticmethod
    def expense_count(
        user_id,
        period=None
    ):

        query = (
            Expense.query.filter_by(
                user_id=user_id
            )
        )

        query = FinanceQueries.apply_date_filter(
            query,
            Expense,
            "expense_date",
            period
        )

        return query.count()

    @staticmethod
    def largest_expense(user_id):

        return (
            Expense.query
            .filter_by(
                user_id=user_id
            )
            .order_by(
                Expense.amount.desc()
            )
            .first()
        )

    @staticmethod
    def latest_expense(user_id):

        return (
            Expense.query
            .filter_by(
                user_id=user_id
            )
            .order_by(
                Expense.expense_date.desc()
            )
            .first()
        )

    @staticmethod
    def recurring_expenses(user_id):

        return (
            Expense.query
            .filter(
                Expense.user_id == user_id,
                Expense.recurring.is_(True)
            )
            .all()
        )

    @staticmethod
    def top_expenses(
        user_id,
        limit=5
    ):

        return (
            Expense.query
            .filter_by(
                user_id=user_id
            )
            .order_by(
                Expense.amount.desc()
            )
            .limit(limit)
            .all()
        )

    @staticmethod
    def top_categories(
        user_id,
        period=None
    ):

        query = (
            db.session.query(
                Expense.category,
                func.sum(
                    Expense.amount
                ).label("total")
            )
            .filter(
                Expense.user_id == user_id
            )
        )

        query = FinanceQueries.apply_date_filter(
            query,
            Expense,
            "expense_date",
            period
        )

        return (
            query.group_by(
                Expense.category
            )
            .order_by(
                func.sum(
                    Expense.amount
                ).desc()
            )
            .all()
        )

    @staticmethod
    def top_merchants(
        user_id,
        period=None
    ):

        query = (
            db.session.query(
                Expense.merchant,
                func.sum(
                    Expense.amount
                ).label("total")
            )
            .filter(
                Expense.user_id == user_id
            )
        )

        query = FinanceQueries.apply_date_filter(
            query,
            Expense,
            "expense_date",
            period
        )

        return (
            query.group_by(
                Expense.merchant
            )
            .order_by(
                func.sum(
                    Expense.amount
                ).desc()
            )
            .all()
        )

    @staticmethod
    def highest_merchant(
        user_id,
        period=None
    ):

        merchants = FinanceQueries.top_merchants(
            user_id,
            period
        )

        if merchants:
            return merchants[0]

        return None

    @staticmethod
    def most_used_payment_method(user_id):

        return (
            db.session.query(
                Expense.payment_method,
                func.count().label("count")
            )
            .filter(
                Expense.user_id == user_id
            )
            .group_by(
                Expense.payment_method
            )
            .order_by(
                func.count().desc()
            )
            .first()
        )

    @staticmethod
    def expense_categories(user_id):

        return (
            db.session.query(
                Expense.category,
                func.sum(
                    Expense.amount
                ).label("total")
            )
            .filter(
                Expense.user_id == user_id
            )
            .group_by(
                Expense.category
            )
            .order_by(
                func.sum(
                    Expense.amount
                ).desc()
            )
            .all()
        )
    
    # =====================================================
    # BUDGET INTELLIGENCE
    # =====================================================

    @staticmethod
    def budget_by_category(user_id, category):

        return (
            Budget.query
            .filter_by(
                user_id=user_id,
                category=category
            )
            .first()
        )


    @staticmethod
    def budget_usage(user_id, category):

        budget = FinanceQueries.budget_by_category(
            user_id,
            category
        )

        if not budget:
            return 0

        spent = FinanceQueries.expense_by_category(
            user_id,
            category
        )

        return spent


    @staticmethod
    def budget_remaining(user_id, category):

        budget = FinanceQueries.budget_by_category(
            user_id,
            category
        )

        if not budget:
            return 0

        spent = FinanceQueries.expense_by_category(
            user_id,
            category
        )

        return max(
            budget.amount - spent,
            0
        )


    @staticmethod
    def budget_percentage_used(user_id, category):

        budget = FinanceQueries.budget_by_category(
            user_id,
            category
        )

        if not budget:
            return 0

        spent = FinanceQueries.expense_by_category(
            user_id,
            category
        )

        if budget.amount == 0:
            return 0

        return round(
            spent / budget.amount * 100,
            2
        )


    @staticmethod
    def budget_overrun(user_id, category):

        budget = FinanceQueries.budget_by_category(
            user_id,
            category
        )

        if not budget:
            return 0

        spent = FinanceQueries.expense_by_category(
            user_id,
            category
        )

        return max(
            spent - budget.amount,
            0
        )


    @staticmethod
    def active_budgets(user_id):

        today = date.today()

        return (
            Budget.query
            .filter(
                Budget.user_id == user_id,
                Budget.start_date <= today,
                Budget.end_date >= today
            )
            .order_by(
                Budget.end_date
            )
            .all()
        )


    @staticmethod
    def expired_budgets(user_id):

        today = date.today()

        return (
            Budget.query
            .filter(
                Budget.user_id == user_id,
                Budget.end_date < today
            )
            .order_by(
                Budget.end_date.desc()
            )
            .all()
        )


    @staticmethod
    def budgets_expiring_soon(user_id, days=7):

        today = date.today()

        future = today + timedelta(days=days)

        return (
            Budget.query
            .filter(
                Budget.user_id == user_id,
                Budget.end_date >= today,
                Budget.end_date <= future
            )
            .order_by(
                Budget.end_date
            )
            .all()
        )
    
    # =====================================================
    # ADVANCED BUDGET ANALYTICS
    # =====================================================

    @staticmethod
    def all_budget_status(user_id):

        budgets = FinanceQueries.active_budgets(user_id)

        report = []

        for budget in budgets:

            spent = FinanceQueries.expense_by_category(
                user_id,
                budget.category
            )

            remaining = budget.amount - spent

            percentage = (
                round((spent / budget.amount) * 100, 2)
                if budget.amount else 0
            )

            report.append({

                "category": budget.category,

                "budget": budget.amount,

                "spent": spent,

                "remaining": remaining,

                "percentage": percentage,

                "status": (
                    "Exceeded"
                    if spent > budget.amount
                    else "Near Limit"
                    if percentage >= 90
                    else "Healthy"
                )

            })

        return report


    @staticmethod
    def exceeded_budgets(user_id):

        budgets = FinanceQueries.active_budgets(user_id)

        exceeded = []

        for budget in budgets:

            spent = FinanceQueries.expense_by_category(
                user_id,
                budget.category
            )

            if spent > budget.amount:

                exceeded.append({

                    "category": budget.category,

                    "budget": budget.amount,

                    "spent": spent,

                    "overrun": spent - budget.amount

                })

        return exceeded


    @staticmethod
    def nearest_budget_limit(user_id):

        budgets = FinanceQueries.active_budgets(user_id)

        closest = None

        highest = -1

        for budget in budgets:

            spent = FinanceQueries.expense_by_category(
                user_id,
                budget.category
            )

            if budget.amount == 0:
                continue

            pct = (spent / budget.amount) * 100

            if pct > highest:

                highest = pct

                closest = {

                    "category": budget.category,

                    "budget": budget.amount,

                    "spent": spent,

                    "percentage": round(pct, 2)

                }

        return closest


    @staticmethod
    def healthiest_budget(user_id):

        budgets = FinanceQueries.active_budgets(user_id)

        best = None

        lowest = 999

        for budget in budgets:

            spent = FinanceQueries.expense_by_category(
                user_id,
                budget.category
            )

            if budget.amount == 0:
                continue

            pct = (spent / budget.amount) * 100

            if pct < lowest:

                lowest = pct

                best = {

                    "category": budget.category,

                    "budget": budget.amount,

                    "spent": spent,

                    "percentage": round(pct, 2)

                }

        return best


    @staticmethod
    def total_budget(user_id):

        return (

            db.session.query(

                func.coalesce(

                    func.sum(Budget.amount),

                    0

                )

            )

            .filter(

                Budget.user_id == user_id

            )

            .scalar()

        )


    @staticmethod
    def total_budget_used(user_id):

        budgets = FinanceQueries.active_budgets(user_id)

        total = 0

        for budget in budgets:

            total += FinanceQueries.expense_by_category(

                user_id,

                budget.category

            )

        return total


    @staticmethod
    def total_budget_remaining(user_id):

        total_budget = FinanceQueries.total_budget(user_id)

        used = FinanceQueries.total_budget_used(user_id)

        return total_budget - used


    @staticmethod
    def overall_budget_percentage(user_id):

        total_budget = FinanceQueries.total_budget(user_id)

        if total_budget == 0:

            return 0

        used = FinanceQueries.total_budget_used(user_id)

        return round(

            used / total_budget * 100,

            2

        )
    
    # =====================================================
    # GOAL INTELLIGENCE
    # =====================================================

    @staticmethod
    def goals(user_id):

        return (
            Goal.query
            .filter_by(user_id=user_id)
            .all()
        )
    
    @staticmethod
    def active_goals(user_id):

        goals = Goal.query.filter_by(
            user_id=user_id
        ).all()

        return [
            goal
            for goal in goals
            if goal.progress_percentage < 100
        ]
    
    @staticmethod
    def completed_goals(user_id):

        goals = FinanceQueries.goals(user_id)

        return [
            goal
            for goal in goals
            if goal.progress_percentage >= 100
        ]
    
    @staticmethod
    def total_goal_target(user_id):

        return (
            db.session.query(
                func.coalesce(
                    func.sum(Goal.target_amount),
                    0
                )
            )
            .filter(
                Goal.user_id == user_id
            )
            .scalar()
        )
    
    @staticmethod
    def total_goal_contributions(user_id):

        return (
            db.session.query(
                func.coalesce(
                    func.sum(
                        GoalContribution.amount
                    ),
                    0
                )
            )
            .join(
                Goal,
                Goal.id == GoalContribution.goal_id
            )
            .filter(
                Goal.user_id == user_id
            )
            .scalar()
        )
    
    @staticmethod
    def goal_contribution(goal_id):

        return (
            db.session.query(
                func.coalesce(
                    func.sum(
                        GoalContribution.amount
                    ),
                    0
                )
            )
            .filter(
                GoalContribution.goal_id == goal_id
            )
            .scalar()
        )
    
    @staticmethod
    def goal_remaining(goal):

        return goal.remaining_amount

    @staticmethod
    def goal_percentage(goal):

        return goal.progress_percentage
    
    @staticmethod
    def goal_progress(goal):

        contributed = goal.saved_amount

        remaining = goal.remaining_amount

        percentage = goal.progress_percentage

        return {

            "goal": goal,

            "contributed": contributed,

            "remaining": remaining,

            "percentage": percentage

        }
    
    @staticmethod
    def closest_goal(user_id):

        goals = FinanceQueries.active_goals(user_id)

        if not goals:
            return None

        return max(
            goals,
            key=lambda g: g.progress_percentage
        )
    
    @staticmethod
    def furthest_goal(user_id):

        goals = FinanceQueries.active_goals(user_id)

        if not goals:
            return None

        return min(
            goals,
            key=lambda g: g.progress_percentage
        )
    
    @staticmethod
    def highest_priority_goal(user_id):

        priorities = {

            "High": 3,

            "Medium": 2,

            "Low": 1

        }

        goals = FinanceQueries.active_goals(user_id)

        if not goals:

            return None

        return sorted(

            goals,

            key=lambda g:

            priorities.get(

                g.priority,

                0

            ),

            reverse=True

        )[0]

    @staticmethod
    def goals_due_soon(user_id, days=30):

        today = date.today()

        deadline = today + timedelta(days=days)

        goals = (
            Goal.query
            .filter(
                Goal.user_id == user_id,
                Goal.target_date >= today,
                Goal.target_date <= deadline
            )
            .all()
        )

        return [
            g
            for g in goals
            if g.progress_percentage < 100
        ]

    @staticmethod
    def overdue_goals(user_id):

        today = date.today()

        goals = (
            Goal.query
            .filter(
                Goal.user_id == user_id,
                Goal.target_date < today
            )
            .all()
        )

        return [
            g
            for g in goals
            if g.progress_percentage < 100
        ]
    
    @staticmethod
    def monthly_required(goal):

        return goal.monthly_contribution

    @staticmethod
    def highest_contributed_goal(user_id):

        goals = FinanceQueries.goals(user_id)

        if not goals:
            return None

        return max(
            goals,
            key=lambda g: g.saved_amount
        )
    
    @staticmethod
    def goal_summary(user_id):

        goals = FinanceQueries.goals(user_id)

        active = FinanceQueries.active_goals(user_id)

        completed = FinanceQueries.completed_goals(user_id)

        return {

            "total": len(goals),

            "active": len(active),

            "completed": len(completed),

            "target": sum(g.target_amount for g in goals),

            "contributed": sum(g.saved_amount for g in goals),

            "remaining": sum(g.remaining_amount for g in goals),

            "completion_percentage": round(
                (
                    sum(g.saved_amount for g in goals)
                    /
                    max(sum(g.target_amount for g in goals), 1)
                ) * 100,
                2
            )
        }
    
    # =====================================================
    # CASH FLOW
    # =====================================================

    @staticmethod
    def monthly_cash_flow(user_id):

        income = FinanceQueries.income_this_month(user_id)

        expense = FinanceQueries.expense_this_month(user_id)

        return {

            "income": income,

            "expense": expense,

            "balance": income - expense

        }
    
    @staticmethod
    def cash_flow_status(user_id):

        flow = FinanceQueries.monthly_cash_flow(user_id)

        if flow["balance"] > 0:

            return "positive"

        elif flow["balance"] < 0:

            return "negative"

        return "neutral"
    
    @staticmethod
    def monthly_income_trend(user_id):

        return (

            db.session.query(

                func.extract(
                    "month",
                    Income.received_date
                ).label("month"),

                func.sum(
                    Income.amount
                ).label("total")

            )

            .filter(

                Income.user_id == user_id

            )

            .group_by(

                func.extract(
                    "month",
                    Income.received_date
                )

            )

            .order_by(

                func.extract(
                    "month",
                    Income.received_date
                )

            )

            .all()

        )
    
    @staticmethod
    def monthly_expense_trend(user_id):

        return (

            db.session.query(

                func.extract(
                    "month",
                    Expense.expense_date
                ).label("month"),

                func.sum(
                    Expense.amount
                ).label("total")

            )

            .filter(

                Expense.user_id == user_id

            )

            .group_by(

                func.extract(
                    "month",
                    Expense.expense_date
                )

            )

            .order_by(

                func.extract(
                    "month",
                    Expense.expense_date
                )

            )

            .all()

        )
    
    @staticmethod
    def best_income_month(user_id):

        data = FinanceQueries.monthly_income_trend(
            user_id
        )

        if not data:

            return None

        return max(
            data,
            key=lambda x: x.total
        )

    @staticmethod
    def highest_expense_month(user_id):

        data = FinanceQueries.monthly_expense_trend(
            user_id
        )

        if not data:

            return None

        return max(
            data,
            key=lambda x: x.total
        )
    
    @staticmethod
    def monthly_savings(user_id):

        incomes = {

            int(x.month): float(x.total)

            for x in FinanceQueries.monthly_income_trend(
                user_id
            )

        }

        expenses = {

            int(x.month): float(x.total)

            for x in FinanceQueries.monthly_expense_trend(
                user_id
            )

        }

        months = sorted(

            set(incomes.keys()) |

            set(expenses.keys())

        )

        results = []

        for month in months:

            income = incomes.get(month, 0)

            expense = expenses.get(month, 0)

            results.append({

                "month": month,

                "income": income,

                "expense": expense,

                "savings": income - expense

            })

        return results
    
    @staticmethod
    def best_savings_month(user_id):

        data = FinanceQueries.monthly_savings(
            user_id
        )

        if not data:

            return None

        return max(

            data,

            key=lambda x: x["savings"]

        )
    
    @staticmethod
    def worst_savings_month(user_id):

        data = FinanceQueries.monthly_savings(
            user_id
        )

        if not data:

            return None

        return min(

            data,

            key=lambda x: x["savings"]

        )
    
    @staticmethod
    def average_monthly_income(user_id):

        data = FinanceQueries.monthly_income_trend(
            user_id
        )

        if not data:

            return 0

        return sum(

            x.total

            for x in data

        ) / len(data)
    
    @staticmethod
    def average_monthly_expense(user_id):

        data = FinanceQueries.monthly_expense_trend(
            user_id
        )

        if not data:

            return 0

        return sum(

            x.total

            for x in data

        ) / len(data)
    
    @staticmethod
    def expense_income_ratio(user_id):

        income = FinanceQueries.total_income(
            user_id
        )

        expense = FinanceQueries.total_expense(
            user_id
        )

        if income == 0:

            return 0

        return round(

            expense / income * 100,

            2

        )
    
    # =====================================================
    # FINANCIAL HEALTH SCORE
    # =====================================================

    @staticmethod
    def savings_score(user_id):

        income = FinanceQueries.total_income(user_id)
        expense = FinanceQueries.total_expense(user_id)

        if income <= 0:
            return 0

        rate = ((income - expense) / income) * 100

        if rate >= 40:
            return 25
        elif rate >= 30:
            return 22
        elif rate >= 20:
            return 18
        elif rate >= 10:
            return 12
        elif rate >= 0:
            return 6

        return 0
    
    @staticmethod
    def budget_score(user_id):

        budgets = FinanceQueries.active_budgets(user_id)

        if not budgets:
            return 10

        score = 25

        for budget in budgets:

            spent = FinanceQueries.expense_by_category(
                user_id,
                budget.category
            )

            if spent > budget.amount:

                score -= 5

            elif spent >= budget.amount * 0.90:

                score -= 2

        return max(score, 0)
    
    @staticmethod
    def goal_score(user_id):

        goals = FinanceQueries.active_goals(user_id)

        if not goals:
            return 10

        percentages = []

        for goal in goals:

            percentages.append(
                FinanceQueries.goal_percentage(goal)
            )

        average = sum(percentages) / len(percentages)

        return round(
            average / 4,
            2
        )

    @staticmethod
    def cashflow_score(user_id):

        income = FinanceQueries.total_income(user_id)
        expense = FinanceQueries.total_expense(user_id)

        if income == 0:

            return 0

        ratio = expense / income

        if ratio <= 0.50:
            return 25

        elif ratio <= 0.60:
            return 22

        elif ratio <= 0.70:
            return 18

        elif ratio <= 0.80:
            return 14

        elif ratio <= 0.90:
            return 8

        return 3
    
    @staticmethod
    def financial_health_score(user_id):

        savings = FinanceQueries.savings_score(user_id)

        budget = FinanceQueries.budget_score(user_id)

        goals = FinanceQueries.goal_score(user_id)

        cashflow = FinanceQueries.cashflow_score(user_id)

        total = round(

            savings +

            budget +

            goals +

            cashflow,

            2

        )

        return {

            "score": total,

            "savings": savings,

            "budget": budget,

            "goals": goals,

            "cashflow": cashflow

        }
    
    @staticmethod
    def financial_grade(score):

        if score >= 90:
            return "A+"

        elif score >= 80:
            return "A"

        elif score >= 70:
            return "B"

        elif score >= 60:
            return "C"

        elif score >= 50:
            return "D"

        return "F"
    
    @staticmethod
    def financial_status(score):

        if score >= 90:
            return "Excellent"

        elif score >= 80:
            return "Very Good"

        elif score >= 70:
            return "Good"

        elif score >= 60:
            return "Fair"

        elif score >= 50:
            return "Needs Improvement"

        return "Critical"
    
    @staticmethod
    def financial_recommendations(user_id):

        report = []

        score = FinanceQueries.financial_health_score(
            user_id
        )

        if score["cashflow"] < 18:

            report.append(

                "Reduce your monthly expenses."

            )

        if score["budget"] < 18:

            report.append(

                "Stay within your budgets."

            )

        if score["goals"] < 18:

            report.append(

                "Increase contributions towards your financial goals."

            )

        if score["savings"] < 18:

            report.append(

                "Increase your savings rate."

            )

        if not report:

            report.append(

                "Excellent financial discipline. Keep it up."

            )

        return report
    
    @staticmethod
    def financial_report(user_id):

        health = FinanceQueries.financial_health_score(
            user_id
        )

        score = health["score"]

        return {

            "score": score,

            "grade": FinanceQueries.financial_grade(score),

            "status": FinanceQueries.financial_status(score),

            "breakdown": health,

            "recommendations":

                FinanceQueries.financial_recommendations(

                    user_id

                )

        }
    
    # -----------------------------------------
    # MONTHLY EXPENSE HISTORY
    # -----------------------------------------

    @staticmethod
    def monthly_expense_history(user_id, months=6):

        from datetime import date
        from sqlalchemy import func

        today = date.today()

        history = []

        year = today.year
        month = today.month

        for _ in range(months):

            total = (
                db.session.query(
                    func.coalesce(func.sum(Expense.amount), 0)
                )
                .filter(
                    Expense.user_id == user_id,
                    func.extract("year", Expense.expense_date) == year,
                    func.extract("month", Expense.expense_date) == month
                )
                .scalar()
            )

            history.insert(0, {
                "year": year,
                "month": month,
                "total": float(total)
            })

            month -= 1

            if month == 0:
                month = 12
                year -= 1

        return history


    # -----------------------------------------
    # EXPENSE TREND
    # -----------------------------------------

    @staticmethod
    def expense_trend(user_id):

        history = FinanceQueries.monthly_expense_history(
            user_id,
            months=2
        )

        if len(history) < 2:
            return None

        previous = history[0]["total"]
        current = history[1]["total"]

        difference = current - previous

        if previous == 0:

            percent = 100 if current > 0 else 0

        else:

            percent = round(
                (difference / previous) * 100,
                2
            )

        if difference > 0:

            direction = "increased"

        elif difference < 0:

            direction = "decreased"

        else:

            direction = "unchanged"

        return {

            "current": current,

            "previous": previous,

            "difference": difference,

            "percent": percent,

            "direction": direction

        }

    