from .queries import FinanceQueries
from .forecasting import Forecast
from .analytics import Analytics
from app.services.dashboard_service import DashboardService

class Advisor:
    """
    Financial Advisory Engine

    Generates personalized financial advice using
    FinanceQueries, Forecast and Analytics.

    This class NEVER queries the database directly.
    """

    # =====================================================
    # MAIN ADVISOR
    # =====================================================

    @staticmethod
    def advise(user_id):

        advice = []

        # ---------------------------------------------
        # Financial Health
        # ---------------------------------------------

        report = FinanceQueries.financial_report(
            user_id
        )

        score = report["score"]

        if score >= 90:

            advice.append(
                "Excellent financial discipline. Keep maintaining your current habits."
            )

        elif score >= 75:

            advice.append(
                "Your finances are healthy. Small improvements could make them even stronger."
            )

        elif score >= 60:

            advice.append(
                "Your finances are fairly stable, but there are areas that need attention."
            )

        else:

            advice.append(
                "Your financial health needs improvement. Focus on reducing expenses and increasing savings."
            )

        # ---------------------------------------------
        # Savings Rate
        # ---------------------------------------------

        income = FinanceQueries.total_income(user_id)
        expense = FinanceQueries.total_expense(user_id)

        if income > 0:

            savings_rate = (
                (income - expense) / income
            ) * 100

            if savings_rate < 20:

                advice.append(
                    "Your savings rate is below 20%. Aim to save at least 20% of your income."
                )

            elif savings_rate >= 40:

                advice.append(
                    "Your savings rate is excellent."
                )

        # ---------------------------------------------
        # Cash Flow
        # ---------------------------------------------

        flow = FinanceQueries.cash_flow_status(
            user_id
        )

        if flow == "negative":

            advice.append(
                "Your cash flow is negative. You're spending more than you earn."
            )

        elif flow == "neutral":

            advice.append(
                "Your income and expenses are almost equal. Build a stronger financial buffer."
            )

        else:

            advice.append(
                "Your cash flow is positive."
            )

        # ---------------------------------------------
        # Budget Analysis
        # ---------------------------------------------

        exceeded = FinanceQueries.exceeded_budgets(
            user_id
        )

        if exceeded:

            for item in exceeded:

                advice.append(

                    f"You exceeded your "

                    f"{item['category']} budget "

                    f"by ₦{item['overrun']:,.2f}."

                )

        else:

            advice.append(
                "All active budgets are under control."
            )

        # ---------------------------------------------
        # Budget Near Limit
        # ---------------------------------------------

        nearest = FinanceQueries.nearest_budget_limit(
            user_id
        )

        if nearest and nearest["percentage"] >= 90:

            advice.append(

                f"Your {nearest['category']} budget "

                f"is {nearest['percentage']}% used."

            )

        # ---------------------------------------------
        # Goals
        # ---------------------------------------------

        goal = FinanceQueries.closest_goal(
            user_id
        )

        if goal:

            pct = FinanceQueries.goal_percentage(
                goal
            )

            advice.append(

                f"Your closest goal "

                f"'{goal.name}' "

                f"is {pct}% complete."

            )

        overdue = FinanceQueries.overdue_goals(
            user_id
        )

        if overdue:

            advice.append(

                f"You have "

                f"{len(overdue)} overdue goal(s)."

            )

        # ==========================================================
        # FORECAST BALANCE
        # ==========================================================

        @staticmethod
        def forecast_balance(user_id):
            """
            Returns the projected month-end savings/balance.
            """

            forecast = DashboardService.month_end_forecast(user_id)

            return forecast.get("projected_savings", 0)

        # ==========================================================
        # FORECAST BALANCE
        # ==========================================================

        @staticmethod
        def forecast_balance(user_id):
            """
            Uses the month-end forecast as the single source of truth.
            """

            forecast = DashboardService.month_end_forecast(user_id)

            return forecast["projected_savings"]

        forecast_balance = FinanceQueries.forecast_balance(user_id)

        if forecast_balance < 0:

            advice.append(
                "Based on your current spending pattern, "
                "you may finish the month with a negative balance."
            )

        else:

            advice.append(
                f"Your projected month-end balance is "
                f"₦{forecast_balance:,.2f}."
            )

        # ---------------------------------------------
        # Expense Trend
        # ---------------------------------------------

        trend = FinanceQueries.expense_trend(
            user_id
        )

        if trend:

            if trend["direction"] == "increased":

                advice.append(

                    f"Your expenses increased by "

                    f"{trend['percent']}% "

                    f"compared with last month."

                )

            elif trend["direction"] == "decreased":

                advice.append(

                    f"Great job. Your expenses decreased "

                    f"by {abs(trend['percent'])}%."

                )

        # ---------------------------------------------
        # Expense / Income Ratio
        # ---------------------------------------------

        ratio = FinanceQueries.expense_income_ratio(
            user_id
        )

        if ratio >= 90:

            advice.append(
                "You spend almost all your income. Consider reducing discretionary expenses."
            )

        elif ratio <= 50:

            advice.append(
                "Excellent expense-to-income ratio."
            )

        return advice

    # =====================================================
    # SHORT SUMMARY
    # =====================================================

    @staticmethod
    def summary(user_id):

        advice = Advisor.advise(user_id)

        if not advice:

            return (
                "No recommendations available."
            )

        return "\n\n".join(

            f"• {item}"

            for item in advice

        )