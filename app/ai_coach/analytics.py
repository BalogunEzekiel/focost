from .queries import FinanceQueries


class Analytics:
    """
    Financial Analytics Engine

    Performs comparisons and trend analysis.

    This class NEVER queries the database directly.
    Everything comes from FinanceQueries.
    """

    # =====================================================
    # PERIOD COMPARISON
    # =====================================================

    @staticmethod
    def compare_periods(user_id, parsed):

        period = parsed.get("period")

        if period == "month":

            current = FinanceQueries.total_expense(
                user_id,
                "month"
            )

            previous = FinanceQueries.total_expense(
                user_id,
                "last_month"
            )

            difference = current - previous

            if previous == 0:

                percent = 100 if current else 0

            else:

                percent = round(
                    difference / previous * 100,
                    2
                )

            direction = (
                "increased"
                if difference > 0
                else "decreased"
                if difference < 0
                else "remained the same"
            )

            return (
                f"This month's expenses are "
                f"₦{current:,.2f}.\n\n"
                f"Last month's expenses were "
                f"₦{previous:,.2f}.\n\n"
                f"Expenses have {direction} "
                f"by ₦{abs(difference):,.2f} "
                f"({abs(percent)}%)."
            )

        return Analytics.expense_trend_summary(user_id)

    # =====================================================
    # EXPENSE TREND
    # =====================================================

    @staticmethod
    def expense_trend_summary(user_id):

        trend = FinanceQueries.expense_trend(
            user_id
        )

        if not trend:

            return "Not enough expense history available."

        return (

            f"Current Month: ₦{trend['current']:,.2f}\n"

            f"Previous Month: ₦{trend['previous']:,.2f}\n"

            f"Difference: ₦{trend['difference']:,.2f}\n"

            f"Change: {trend['percent']}%\n"

            f"Your expenses have "

            f"{trend['direction']}."

        )

    # =====================================================
    # MONTHLY HISTORY
    # =====================================================

    @staticmethod
    def monthly_history(user_id):

        return FinanceQueries.monthly_expense_history(
            user_id,
            months=6
        )

    # =====================================================
    # INCOME TREND
    # =====================================================

    @staticmethod
    def income_trend(user_id):

        return FinanceQueries.monthly_income_trend(
            user_id
        )

    # =====================================================
    # EXPENSE TREND
    # =====================================================

    @staticmethod
    def monthly_expense_trend(user_id):

        return FinanceQueries.monthly_expense_trend(
            user_id
        )

    # =====================================================
    # SAVINGS TREND
    # =====================================================

    @staticmethod
    def savings_trend(user_id):

        return FinanceQueries.monthly_savings(
            user_id
        )

    # =====================================================
    # BEST MONTHS
    # =====================================================

    @staticmethod
    def best_income_month(user_id):

        return FinanceQueries.best_income_month(
            user_id
        )

    @staticmethod
    def highest_expense_month(user_id):

        return FinanceQueries.highest_expense_month(
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
    # AVERAGES
    # =====================================================

    @staticmethod
    def average_income(user_id):

        return FinanceQueries.average_monthly_income(
            user_id
        )

    @staticmethod
    def average_expense(user_id):

        return FinanceQueries.average_monthly_expense(
            user_id
        )

    # =====================================================
    # EXPENSE / INCOME RATIO
    # =====================================================

    @staticmethod
    def expense_income_ratio(user_id):

        return FinanceQueries.expense_income_ratio(
            user_id
        )

    # =====================================================
    # COMPLETE ANALYTICS SUMMARY
    # =====================================================

    @staticmethod
    def summary(user_id):

        return {

            "expense_trend":
                FinanceQueries.expense_trend(
                    user_id
                ),

            "best_income_month":
                FinanceQueries.best_income_month(
                    user_id
                ),

            "highest_expense_month":
                FinanceQueries.highest_expense_month(
                    user_id
                ),

            "best_savings_month":
                FinanceQueries.best_savings_month(
                    user_id
                ),

            "worst_savings_month":
                FinanceQueries.worst_savings_month(
                    user_id
                ),

            "average_income":
                FinanceQueries.average_monthly_income(
                    user_id
                ),

            "average_expense":
                FinanceQueries.average_monthly_expense(
                    user_id
                ),

            "expense_income_ratio":
                FinanceQueries.expense_income_ratio(
                    user_id
                )

        }