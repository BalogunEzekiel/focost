from calendar import monthrange
from datetime import date

from .queries import FinanceQueries
from app.services.dashboard_service import DashboardService


class Forecast:
    """
    Financial Forecasting Engine

    Uses DashboardService.month_end_forecast()
    as the single source of truth.

    This ensures the AI Coach and Dashboard
    always return identical forecast results.
    """

    # =====================================================
    # DATE HELPERS
    # =====================================================

    @staticmethod
    def _month_progress():

        today = date.today()

        days_elapsed = max(today.day, 1)

        days_in_month = monthrange(
            today.year,
            today.month
        )[1]

        return {

            "elapsed": days_elapsed,

            "remaining": days_in_month - days_elapsed,

            "total": days_in_month

        }

    # =====================================================
    # DASHBOARD FORECAST
    # =====================================================

    @staticmethod
    def _forecast(user_id):
        """
        Returns the dashboard forecast dictionary.

        {
            projected_income,
            projected_expenses,
            projected_savings,
            forecast_status
        }
        """

        return DashboardService.month_end_forecast(user_id)

    # =====================================================
    # DAILY EXPENSE RATE
    # =====================================================

    @staticmethod
    def daily_expense_rate(user_id):

        info = Forecast._month_progress()

        spent = FinanceQueries.total_expense(
            user_id,
            "month"
        )

        if info["elapsed"] == 0:

            return 0

        return spent / info["elapsed"]

    # =====================================================
    # DAILY INCOME RATE
    # =====================================================

    @staticmethod
    def daily_income_rate(user_id):

        info = Forecast._month_progress()

        income = FinanceQueries.total_income(
            user_id,
            "month"
        )

        if info["elapsed"] == 0:

            return 0

        return income / info["elapsed"]

    # =====================================================
    # FORECAST INCOME
    # =====================================================

    @staticmethod
    def forecast_income(user_id):

        return Forecast._forecast(user_id)[
            "projected_income"
        ]

    # =====================================================
    # FORECAST EXPENSE
    # =====================================================

    @staticmethod
    def forecast_expense(user_id):

        return Forecast._forecast(user_id)[
            "projected_expenses"
        ]

    # =====================================================
    # FORECAST BALANCE
    # =====================================================

    @staticmethod
    def forecast_balance(user_id):

        return Forecast._forecast(user_id)[
            "projected_savings"
        ]

    # =====================================================
    # FORECAST SAVINGS
    # =====================================================

    @staticmethod
    def forecast_savings(user_id):

        return Forecast.forecast_balance(
            user_id
        )

    # =====================================================
    # FORECAST STATUS
    # =====================================================

    @staticmethod
    def forecast_status(user_id):

        return Forecast._forecast(user_id)[
            "forecast_status"
        ]

    # =====================================================
    # GENERATE AI FORECAST
    # =====================================================

    @staticmethod
    def generate(user_id):

        forecast = Forecast._forecast(
            user_id
        )

        return (

            "📈 Month-End Forecast\n\n"

            f"Projected Income: "
            f"₦{forecast['projected_income']:,.2f}\n"

            f"Projected Expenses: "
            f"₦{forecast['projected_expenses']:,.2f}\n"

            f"Projected Savings: "
            f"₦{forecast['projected_savings']:,.2f}\n\n"

            f"{forecast['forecast_status']}"

        )

    # =====================================================
    # SUMMARY
    # =====================================================

    @staticmethod
    def summary(user_id):

        forecast = Forecast._forecast(
            user_id
        )

        return {

            "daily_income":

                Forecast.daily_income_rate(
                    user_id
                ),

            "daily_expense":

                Forecast.daily_expense_rate(
                    user_id
                ),

            "forecast_income":

                forecast["projected_income"],

            "forecast_expense":

                forecast["projected_expenses"],

            "forecast_balance":

                forecast["projected_savings"],

            "forecast_savings":

                forecast["projected_savings"],

            "forecast_status":

                forecast["forecast_status"]

        }