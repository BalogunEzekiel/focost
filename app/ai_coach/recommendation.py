from .queries import FinanceQueries
from .forecasting import Forecast
from .analytics import Analytics


class Recommendation:
    """
    Financial Recommendation Engine

    Produces actionable recommendations.

    Never queries the database directly.
    """

    # =====================================================
    # MAIN ENGINE
    # =====================================================

    @staticmethod
    def generate(user_id):

        recommendations = []

        recommendations.extend(
            Recommendation.reduce_spending(user_id)
        )

        recommendations.extend(
            Recommendation.budget_recommendations(user_id)
        )

        recommendations.extend(
            Recommendation.goal_recommendations(user_id)
        )

        recommendations.extend(
            Recommendation.cashflow_recommendations(user_id)
        )

        recommendations.extend(
            Recommendation.health_recommendations(user_id)
        )

        # Remove duplicates while preserving order

        unique = []

        for item in recommendations:

            if item not in unique:
                unique.append(item)

        return unique

    # =====================================================
    # REDUCE SPENDING
    # =====================================================

    @staticmethod
    def reduce_spending(user_id):

        tips = []

        categories = FinanceQueries.top_categories(
            user_id,
            "month"
        )

        if not categories:

            return [
                "No expenses found to analyze."
            ]

        top = categories[0]

        tips.append(

            f"Your highest spending category this month is "

            f"{top.category} "

            f"(₦{top.total:,.2f})."

        )

        tips.append(

            f"Reducing spending in {top.category} "

            f"would have the greatest impact."

        )

        ratio = FinanceQueries.expense_income_ratio(
            user_id
        )

        if ratio > 80:

            tips.append(

                "Your expenses exceed 80% of your income. "

                "Aim for less than 70%."

            )

        trend = FinanceQueries.expense_trend(
            user_id
        )

        if trend and trend["direction"] == "increased":

            tips.append(

                f"Expenses increased "

                f"{trend['percent']}% "

                f"compared with last month."

            )

        return tips

    # =====================================================
    # BUDGET
    # =====================================================

    @staticmethod
    def budget_recommendations(user_id):

        advice = []

        exceeded = FinanceQueries.exceeded_budgets(
            user_id
        )

        if exceeded:

            for item in exceeded:

                advice.append(

                    f"Increase or review your "

                    f"{item['category']} budget "

                    f"because you exceeded it by "

                    f"₦{item['overrun']:,.2f}."

                )

        nearest = FinanceQueries.nearest_budget_limit(
            user_id
        )

        if nearest:

            if nearest["percentage"] >= 90:

                advice.append(

                    f"Your {nearest['category']} budget "

                    f"is almost exhausted."

                )

        healthiest = FinanceQueries.healthiest_budget(
            user_id
        )

        if healthiest:

            advice.append(

                f"Your {healthiest['category']} budget "

                f"is well managed."

            )

        return advice

    # =====================================================
    # GOALS
    # =====================================================

    @staticmethod
    def goal_recommendations(user_id):

        advice = []

        closest = FinanceQueries.closest_goal(
            user_id
        )

        if closest:

            monthly = FinanceQueries.monthly_required(
                closest
            )

            advice.append(

                f"Save about "

                f"₦{monthly:,.2f} "

                f"per month to reach "

                f"'{closest.name}'."

            )

        overdue = FinanceQueries.overdue_goals(
            user_id
        )

        if overdue:

            advice.append(

                f"You have "

                f"{len(overdue)} overdue goal(s)."

            )

        due = FinanceQueries.goals_due_soon(
            user_id
        )

        if due:

            advice.append(

                f"{len(due)} goal(s) "

                f"are approaching their deadline."

            )

        return advice

    # =====================================================
    # CASH FLOW
    # =====================================================

    @staticmethod
    def cashflow_recommendations(user_id):

        advice = []

        flow = FinanceQueries.cash_flow_status(
            user_id
        )

        if flow == "negative":

            advice.append(

                "Your expenses exceed your income."

            )

            advice.append(

                "Reduce discretionary spending "

                "or increase your income."

            )

        elif flow == "neutral":

            advice.append(

                "Build a larger monthly surplus."

            )

        else:

            advice.append(

                "Maintain your positive cash flow."

            )

        balance = Forecast.forecast_balance(
            user_id
        )

        if balance < 0:

            advice.append(

                "Current spending may lead to a "

                "negative month-end balance."

            )

        return advice

    # =====================================================
    # FINANCIAL HEALTH
    # =====================================================

    @staticmethod
    def health_recommendations(user_id):

        report = FinanceQueries.financial_report(
            user_id
        )

        advice = []

        advice.extend(
            report["recommendations"]
        )

        score = report["score"]

        if score >= 90:

            advice.append(

                "Keep following your current "

                "financial habits."

            )

        elif score < 60:

            advice.append(

                "Focus on budgeting, saving, "

                "and reducing unnecessary expenses."

            )

        return advice

    # =====================================================
    # SHORT SUMMARY
    # =====================================================

    @staticmethod
    def summary(user_id):

        return "\n\n".join(

            f"• {item}"

            for item in Recommendation.generate(
                user_id
            )

        )