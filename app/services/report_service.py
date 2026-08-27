from datetime import date, datetime

from sqlalchemy import func, or_

from app.models.income import Income
from app.models.expense import Expense


class ReportService:
    """
    Centralized financial reporting service.

    All reporting queries are scoped to the authenticated user.

    Supported filters:
        - start_date
        - end_date
        - category

    The filtering is performed at database-query level rather than
    filtering records after retrieval.
    """

    # ==========================================================
    # PUBLIC REPORT API
    # ==========================================================

    @staticmethod
    def summary(
        user_id,
        start_date=None,
        end_date=None,
        category=None,
    ):
        """
        Generate a complete financial report.

        Parameters
        ----------
        user_id:
            Authenticated user's database ID.

        start_date:
            Optional inclusive start date.

        end_date:
            Optional inclusive end date.

        category:
            Optional category filter.

        Returns
        -------
        dict
            Complete report payload suitable for the Reports UI.
        """

        # ------------------------------------------------------
        # Normalize filters
        # ------------------------------------------------------

        start_date = ReportService._normalize_date(start_date)
        end_date = ReportService._normalize_date(end_date)

        category = ReportService._normalize_category(category)

        # ------------------------------------------------------
        # Validate date range
        # ------------------------------------------------------

        if (
            start_date
            and end_date
            and start_date > end_date
        ):
            raise ValueError(
                "start_date cannot be later than end_date."
            )

        # ======================================================
        # BASE QUERIES
        # ======================================================

        income_query = Income.query.filter(
            Income.user_id == user_id
        )

        expense_query = Expense.query.filter(
            Expense.user_id == user_id
        )

        # ======================================================
        # APPLY DATE FILTERS
        # ======================================================

        if start_date:

            income_query = income_query.filter(
                Income.received_date >= start_date
            )

            expense_query = expense_query.filter(
                Expense.expense_date >= start_date
            )

        if end_date:

            income_query = income_query.filter(
                Income.received_date <= end_date
            )

            expense_query = expense_query.filter(
                Expense.expense_date <= end_date
            )

        # ======================================================
        # APPLY CATEGORY FILTER
        # ======================================================

        if category:

            income_query = income_query.filter(
                Income.category == category
            )

            expense_query = expense_query.filter(
                Expense.category == category
            )

        # ======================================================
        # TOTAL INCOME
        # ======================================================

        income = (
            income_query
            .with_entities(
                func.coalesce(
                    func.sum(Income.amount),
                    0
                )
            )
            .scalar()
            or 0
        )

        # ======================================================
        # TOTAL EXPENSES
        # ======================================================

        expenses = (
            expense_query
            .with_entities(
                func.coalesce(
                    func.sum(Expense.amount),
                    0
                )
            )
            .scalar()
            or 0
        )

        # ======================================================
        # SAVINGS
        # ======================================================

        savings = income - expenses

        # ======================================================
        # TRANSACTION COUNTS
        # ======================================================

        income_count = (
            income_query
            .with_entities(
                func.count(Income.id)
            )
            .scalar()
            or 0
        )

        expense_count = (
            expense_query
            .with_entities(
                func.count(Expense.id)
            )
            .scalar()
            or 0
        )

        transactions = (
            income_count +
            expense_count
        )

        # ======================================================
        # INCOME BY CATEGORY
        # ======================================================

        income_categories = (
            income_query
            .with_entities(
                Income.category,
                func.sum(Income.amount)
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

        # ======================================================
        # EXPENSE BY CATEGORY
        # ======================================================

        expense_categories = (
            expense_query
            .with_entities(
                Expense.category,
                func.sum(Expense.amount)
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

        # ======================================================
        # MONTHLY INCOME
        # ======================================================

        income_month_expression = func.strftime(
            "%Y-%m",
            Income.received_date
        )

        monthly_income = (
            income_query
            .with_entities(
                income_month_expression.label(
                    "month"
                ),
                func.sum(
                    Income.amount
                ).label(
                    "amount"
                )
            )
            .group_by(
                income_month_expression
            )
            .order_by(
                income_month_expression
            )
            .all()
        )

        # ======================================================
        # MONTHLY EXPENSE
        # ======================================================

        expense_month_expression = func.strftime(
            "%Y-%m",
            Expense.expense_date
        )

        monthly_expense = (
            expense_query
            .with_entities(
                expense_month_expression.label(
                    "month"
                ),
                func.sum(
                    Expense.amount
                ).label(
                    "amount"
                )
            )
            .group_by(
                expense_month_expression
            )
            .order_by(
                expense_month_expression
            )
            .all()
        )

        # ======================================================
        # NORMALIZE CATEGORY DATA
        # ======================================================

        income_category_labels = [
            row[0]
            for row in income_categories
            if row[0]
        ]

        income_category_values = [
            float(row[1] or 0)
            for row in income_categories
        ]

        expense_category_labels = [
            row[0]
            for row in expense_categories
            if row[0]
        ]

        expense_category_values = [
            float(row[1] or 0)
            for row in expense_categories
        ]

        # ======================================================
        # NORMALIZE MONTHLY DATA
        # ======================================================

        income_by_month = {
            row[0]: float(row[1] or 0)
            for row in monthly_income
            if row[0]
        }

        expense_by_month = {
            row[0]: float(row[1] or 0)
            for row in monthly_expense
            if row[0]
        }

        # ======================================================
        # COMBINED MONTH AXIS
        # ======================================================

        months = sorted(
            set(income_by_month)
            |
            set(expense_by_month)
        )

        monthly_income_values = [
            income_by_month.get(
                month,
                0
            )
            for month in months
        ]

        monthly_expense_values = [
            expense_by_month.get(
                month,
                0
            )
            for month in months
        ]

        # ======================================================
        # SAVINGS RATE
        # ======================================================

        savings_rate = (
            (savings / income) * 100
            if income
            else 0
        )

        # ======================================================
        # EXPENSE RATIO
        # ======================================================

        expense_ratio = (
            (expenses / income) * 100
            if income
            else 0
        )

        # ======================================================
        # TOP INCOME CATEGORY
        # ======================================================

        top_income_category = None

        if income_categories:

            category_name, category_amount = (
                income_categories[0]
            )

            top_income_category = {
                "name": category_name,
                "amount": float(
                    category_amount or 0
                ),
            }

        # ======================================================
        # TOP EXPENSE CATEGORY
        # ======================================================

        top_expense_category = None

        if expense_categories:

            category_name, category_amount = (
                expense_categories[0]
            )

            top_expense_category = {
                "name": category_name,
                "amount": float(
                    category_amount or 0
                ),
            }

        # ======================================================
        # AVAILABLE CATEGORIES
        # ======================================================

        categories = sorted(
            {
                category
                for category in (
                    income_category_labels
                    +
                    expense_category_labels
                )
                if category
            }
        )

        # ======================================================
        # FINAL REPORT
        # ======================================================

        return {

            # --------------------------------------------------
            # FILTER STATE
            # --------------------------------------------------

            "filters": {
                "start_date": (
                    start_date.isoformat()
                    if start_date
                    else None
                ),

                "end_date": (
                    end_date.isoformat()
                    if end_date
                    else None
                ),

                "category": category,
            },

            # --------------------------------------------------
            # KPI
            # --------------------------------------------------

            "income": float(income),

            "expenses": float(expenses),

            "savings": float(savings),

            "transactions": int(
                transactions
            ),

            # --------------------------------------------------
            # FINANCIAL RATIOS
            # --------------------------------------------------

            "savings_rate": round(
                savings_rate,
                2
            ),

            "expense_ratio": round(
                expense_ratio,
                2
            ),

            # --------------------------------------------------
            # CATEGORY DATA
            # --------------------------------------------------

            "categories": categories,

            "income_categories": (
                income_categories
            ),

            "expense_categories": (
                expense_categories
            ),

            "income_category_labels": (
                income_category_labels
            ),

            "income_category_values": (
                income_category_values
            ),

            "expense_category_labels": (
                expense_category_labels
            ),

            "expense_category_values": (
                expense_category_values
            ),

            # --------------------------------------------------
            # MONTHLY TREND
            # --------------------------------------------------

            "months": months,

            "monthly_income": (
                monthly_income_values
            ),

            "monthly_expenses": (
                monthly_expense_values
            ),

            # --------------------------------------------------
            # INSIGHTS
            # --------------------------------------------------

            "top_income_category": (
                top_income_category
            ),

            "top_expense_category": (
                top_expense_category
            ),
        }

    # ==========================================================
    # FILTER HELPERS
    # ==========================================================

    @staticmethod
    def _normalize_date(value):
        """
        Convert supported date formats into datetime.date.

        Supported:
            - datetime.date
            - datetime.datetime
            - YYYY-MM-DD string
            - None / empty string
        """

        if value is None:
            return None

        if isinstance(
            value,
            datetime
        ):
            return value.date()

        if isinstance(
            value,
            date
        ):
            return value

        if isinstance(
            value,
            str
        ):

            value = value.strip()

            if not value:
                return None

            try:
                return datetime.strptime(
                    value,
                    "%Y-%m-%d"
                ).date()

            except ValueError as exc:

                raise ValueError(
                    "Date must use YYYY-MM-DD format."
                ) from exc

        raise ValueError(
            "Unsupported date value."
        )

    @staticmethod
    def _normalize_category(category):
        """
        Normalize category input.
        """

        if category is None:
            return None

        if not isinstance(
            category,
            str
        ):
            raise ValueError(
                "Category must be a string."
            )

        category = category.strip()

        return category or None