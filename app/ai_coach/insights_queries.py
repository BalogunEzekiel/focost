from sqlalchemy import func

from app.extensions import db

from app.models.income import Income
from app.models.expense import Expense
from .queries import FinanceQueries

class InsightQueries:
    """
    Thin wrapper around FinanceQueries.

    This class exists so that older AI modules can continue
    calling InsightQueries while all database access remains
    centralized inside FinanceQueries.
    """

    # =====================================================
    # EXPENSE TREND
    # =====================================================

    @staticmethod
    def expense_trend(user_id):
        return FinanceQueries.expense_trend(user_id)

    # =====================================================
    # CATEGORY INSIGHTS
    # =====================================================

    @staticmethod
    def highest_category(user_id, period=None):

        categories = FinanceQueries.top_categories(
            user_id,
            period
        )

        if categories:
            return categories[0]

        return None

    @staticmethod
    def categories(user_id, period=None):

        return FinanceQueries.top_categories(
            user_id,
            period
        )

    # =====================================================
    # MERCHANT INSIGHTS
    # =====================================================

    @staticmethod
    def highest_merchant(user_id, period=None):

        return FinanceQueries.highest_merchant(
            user_id,
            period
        )

    @staticmethod
    def merchants(user_id, period=None):

        return FinanceQueries.top_merchants(
            user_id,
            period
        )

    # =====================================================
    # PAYMENT METHODS
    # =====================================================

    @staticmethod
    def payment_method(user_id):

        return FinanceQueries.most_used_payment_method(
            user_id
        )

    # =====================================================
    # INCOME SOURCES
    # =====================================================

    @staticmethod
    def highest_income_source(user_id):

        sources = FinanceQueries.income_sources(
            user_id
        )

        if sources:
            return sources[0]

        return None

    @staticmethod
    def income_sources(user_id):

        return FinanceQueries.income_sources(
            user_id
        )

    # =====================================================
    # CASH FLOW
    # =====================================================

    @staticmethod
    def cash_flow(user_id):

        return FinanceQueries.monthly_cash_flow(
            user_id
        )

    @staticmethod
    def cash_flow_status(user_id):

        return FinanceQueries.cash_flow_status(
            user_id
        )

    # =====================================================
    # SAVINGS
    # =====================================================

    @staticmethod
    def savings_rate(user_id):

        income = FinanceQueries.total_income(user_id)

        expense = FinanceQueries.total_expense(user_id)

        if income <= 0:
            return 0

        return round(
            ((income - expense) / income) * 100,
            2
        )

    @staticmethod
    def monthly_savings(user_id):

        return FinanceQueries.monthly_savings(
            user_id
        )

    @staticmethod
    def best_savings_month(user_id):

        return FinanceQueries.best_savings_month(
            user_id
        )

    @staticmethod
    def worst_savings_month(user_id):

        return FinanceQueries.worst_savings_month(
            user_id
        )

    # =====================================================
    # RATIOS
    # =====================================================

    @staticmethod
    def expense_income_ratio(user_id):

        return FinanceQueries.expense_income_ratio(
            user_id
        )

    # =====================================================
    # FINANCIAL HEALTH
    # =====================================================

    @staticmethod
    def financial_health(user_id):

        return FinanceQueries.financial_report(
            user_id
        )

    # =====================================================
    # BUDGET
    # =====================================================

    @staticmethod
    def budget_report(user_id):

        return FinanceQueries.all_budget_status(
            user_id
        )

    @staticmethod
    def exceeded_budgets(user_id):

        return FinanceQueries.exceeded_budgets(
            user_id
        )

    @staticmethod
    def nearest_budget_limit(user_id):

        return FinanceQueries.nearest_budget_limit(
            user_id
        )

    # =====================================================
    # GOALS
    # =====================================================

    @staticmethod
    def goal_summary(user_id):

        return FinanceQueries.goal_summary(
            user_id
        )

    @staticmethod
    def closest_goal(user_id):

        return FinanceQueries.closest_goal(
            user_id
        )

    @staticmethod
    def highest_priority_goal(user_id):

        return FinanceQueries.highest_priority_goal(
            user_id
        )

    @staticmethod
    def goals_due_soon(user_id):

        return FinanceQueries.goals_due_soon(
            user_id
        )

    @staticmethod
    def overdue_goals(user_id):

        return FinanceQueries.overdue_goals(
            user_id
        )

    # ---------------------------------------------------------
    # Highest expense category
    # ---------------------------------------------------------

    @staticmethod
    def highest_expense_category(user_id):

        return (
            db.session.query(
                Expense.category,
                func.sum(Expense.amount).label("total")
            )
            .filter(
                Expense.user_id == user_id
            )
            .group_by(
                Expense.category
            )
            .order_by(
                func.sum(Expense.amount).desc()
            )
            .first()
        )

    # ---------------------------------------------------------
    # Lowest expense category
    # ---------------------------------------------------------

    @staticmethod
    def lowest_expense_category(user_id):

        return (
            db.session.query(
                Expense.category,
                func.sum(Expense.amount).label("total")
            )
            .filter(
                Expense.user_id == user_id
            )
            .group_by(
                Expense.category
            )
            .order_by(
                func.sum(Expense.amount)
            )
            .first()
        )

    # ---------------------------------------------------------
    # Largest income source
    # ---------------------------------------------------------

    @staticmethod
    def largest_income_source(user_id):

        return (
            db.session.query(
                Income.source,
                func.sum(Income.amount).label("total")
            )
            .filter(
                Income.user_id == user_id
            )
            .group_by(
                Income.source
            )
            .order_by(
                func.sum(Income.amount).desc()
            )
            .first()
        )

    # ---------------------------------------------------------
    # Largest income category
    # ---------------------------------------------------------

    @staticmethod
    def largest_income_category(user_id):

        return (
            db.session.query(
                Income.category,
                func.sum(Income.amount).label("total")
            )
            .filter(
                Income.user_id == user_id
            )
            .group_by(
                Income.category
            )
            .order_by(
                func.sum(Income.amount).desc()
            )
            .first()
        )

    # ---------------------------------------------------------
    # Largest Merchant
    # ---------------------------------------------------------

    @staticmethod
    def largest_merchant(user_id):

        return (
            db.session.query(
                Expense.merchant,
                func.sum(Expense.amount).label("total")
            )
            .filter(
                Expense.user_id == user_id
            )
            .group_by(
                Expense.merchant
            )
            .order_by(
                func.sum(Expense.amount).desc()
            )
            .first()
        )

    # ---------------------------------------------------------
    # Average Expense
    # ---------------------------------------------------------

    @staticmethod
    def average_expense(user_id):

        avg = (
            db.session.query(
                func.avg(Expense.amount)
            )
            .filter(
                Expense.user_id == user_id
            )
            .scalar()
        )

        return avg or 0

    # ---------------------------------------------------------
    # Average Income
    # ---------------------------------------------------------

    @staticmethod
    def average_income(user_id):

        avg = (
            db.session.query(
                func.avg(Income.amount)
            )
            .filter(
                Income.user_id == user_id
            )
            .scalar()
        )

        return avg or 0

    # ---------------------------------------------------------
    # Largest Expense
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Largest Income
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Total Merchants
    # ---------------------------------------------------------

    @staticmethod
    def merchant_count(user_id):

        return (
            db.session.query(
                func.count(
                    func.distinct(
                        Expense.merchant
                    )
                )
            )
            .filter(
                Expense.user_id == user_id
            )
            .scalar()
        )

    # ---------------------------------------------------------
    # Total Categories
    # ---------------------------------------------------------

    @staticmethod
    def category_count(user_id):

        return (
            db.session.query(
                func.count(
                    func.distinct(
                        Expense.category
                    )
                )
            )
            .filter(
                Expense.user_id == user_id
            )
            .scalar()
        )

    # ---------------------------------------------------------
    # Expense Transactions
    # ---------------------------------------------------------

    @staticmethod
    def expense_transactions(user_id):

        return (
            Expense.query
            .filter_by(
                user_id=user_id
            )
            .count()
        )

    # ---------------------------------------------------------
    # Income Transactions
    # ---------------------------------------------------------

    @staticmethod
    def income_transactions(user_id):

        return (
            Income.query
            .filter_by(
                user_id=user_id
            )
            .count()
        )

    # ---------------------------------------------------------
    # Average Daily Spending
    # ---------------------------------------------------------

    @staticmethod
    def average_daily_spending(user_id):

        total = (
            db.session.query(
                func.coalesce(
                    func.sum(
                        Expense.amount
                    ),
                    0
                )
            )
            .filter(
                Expense.user_id == user_id
            )
            .scalar()
        )

        days = (
            db.session.query(
                func.count(
                    func.distinct(
                        Expense.expense_date
                    )
                )
            )
            .filter(
                Expense.user_id == user_id
            )
            .scalar()
        )

        if not days:
            return 0

        return total / days