class ResponseBuilder:
    """
    Central Response Formatting Engine.

    All user-facing text should be generated here.

    This keeps the service layer clean.
    """

    # =====================================================
    # CURRENCY
    # =====================================================

    @staticmethod
    def money(value):

        return f"₦{float(value):,.2f}"

    # =====================================================
    # BUDGET REPORT
    # =====================================================

    @staticmethod
    def budget_report(report):

        if not report:

            return "You do not have any active budgets."

        lines = ["📊 Budget Status\n"]

        for item in report:

            lines.append(

                f"• {item['category']}\n"

                f"  Budget: {ResponseBuilder.money(item['budget'])}\n"

                f"  Spent: {ResponseBuilder.money(item['spent'])}\n"

                f"  Remaining: {ResponseBuilder.money(item['remaining'])}\n"

                f"  Used: {item['percentage']}%\n"

                f"  Status: {item['status']}\n"

            )

        return "\n".join(lines)

    # =====================================================
    # GOAL SUMMARY
    # =====================================================

    @staticmethod
    def goal_summary(summary):

        return (

            "🎯 Goal Summary\n\n"

            f"Total Goals: {summary['total']}\n"

            f"Active Goals: {summary['active']}\n"

            f"Completed Goals: {summary['completed']}\n"

            f"Target Amount: "

            f"{ResponseBuilder.money(summary['target'])}\n"

            f"Contributed: "

            f"{ResponseBuilder.money(summary['contributed'])}"

        )

    # =====================================================
    # GOAL DETAILS
    # =====================================================

    @staticmethod
    def goal_progress(progress):

        goal = progress["goal"]

        return (

            f"🎯 {goal.name}\n\n"

            f"Target: "

            f"{ResponseBuilder.money(goal.target_amount)}\n"

            f"Saved: "

            f"{ResponseBuilder.money(progress['contributed'])}\n"

            f"Remaining: "

            f"{ResponseBuilder.money(progress['remaining'])}\n"

            f"Completed: "

            f"{progress['percentage']}%"

        )

    # =====================================================
    # FINANCIAL HEALTH
    # =====================================================

    @staticmethod
    def financial_health(report):

        lines = [

            "❤️ Financial Health Report",

            "",

            f"Overall Score: {report['score']}/100",

            f"Grade: {report['grade']}",

            f"Status: {report['status']}",

            "",

            "Breakdown:",

            f"• Savings: {report['breakdown']['savings']}",

            f"• Budget: {report['breakdown']['budget']}",

            f"• Goals: {report['breakdown']['goals']}",

            f"• Cash Flow: {report['breakdown']['cashflow']}",

            "",

            "Recommendations:"

        ]

        for recommendation in report["recommendations"]:

            lines.append(

                f"• {recommendation}"

            )

        return "\n".join(lines)

    # =====================================================
    # FORECAST
    # =====================================================

    @staticmethod
    def forecast(summary):

        return (

            "📈 Month-End Forecast\n\n"

            f"Projected Income: "

            f"{ResponseBuilder.money(summary['forecast_income'])}\n"

            f"Projected Expenses: "

            f"{ResponseBuilder.money(summary['forecast_expense'])}\n"

            f"Projected Balance: "

            f"{ResponseBuilder.money(summary['forecast_balance'])}\n"

            f"Projected Savings: "

            f"{ResponseBuilder.money(summary['forecast_savings'])}\n\n"

            f"Daily Income: "

            f"{ResponseBuilder.money(summary['daily_income'])}\n"

            f"Daily Spending: "

            f"{ResponseBuilder.money(summary['daily_expense'])}\n\n"

            f"Spending Pace: "

            f"{summary['spending_pace']}\n\n"

            f"Budget Risk:\n"

            f"{summary['budget_risk']}"

        )

    # =====================================================
    # ANALYTICS
    # =====================================================

    @staticmethod
    def analytics(summary):

        lines = [

            "📊 Financial Analytics",

            "",

            f"Average Monthly Income: "

            f"{ResponseBuilder.money(summary['average_income'])}",

            f"Average Monthly Expense: "

            f"{ResponseBuilder.money(summary['average_expense'])}",

            f"Expense/Income Ratio: "

            f"{summary['expense_income_ratio']}%",

            ""

        ]

        trend = summary.get("expense_trend")

        if trend:

            lines.extend([

                "Expense Trend:",

                f"Current: "

                f"{ResponseBuilder.money(trend['current'])}",

                f"Previous: "

                f"{ResponseBuilder.money(trend['previous'])}",

                f"Difference: "

                f"{ResponseBuilder.money(trend['difference'])}",

                f"Change: "

                f"{trend['percent']}%",

                f"Direction: "

                f"{trend['direction']}",

                ""

            ])

        best_income = summary.get("best_income_month")

        if best_income:

            lines.append(

                f"Best Income Month: "

                f"Month {int(best_income.month)} "

                f"({ResponseBuilder.money(best_income.total)})"

            )

        highest_expense = summary.get("highest_expense_month")

        if highest_expense:

            lines.append(

                f"Highest Expense Month: "

                f"Month {int(highest_expense.month)} "

                f"({ResponseBuilder.money(highest_expense.total)})"

            )

        best_savings = summary.get("best_savings_month")

        if best_savings:

            lines.append(

                f"Best Savings Month: "

                f"Month {best_savings['month']} "

                f"({ResponseBuilder.money(best_savings['savings'])})"

            )

        worst_savings = summary.get("worst_savings_month")

        if worst_savings:

            lines.append(

                f"Worst Savings Month: "

                f"Month {worst_savings['month']} "

                f"({ResponseBuilder.money(worst_savings['savings'])})"

            )

        return "\n".join(lines)

    # =====================================================
    # RECOMMENDATIONS
    # =====================================================

    @staticmethod
    def recommendations(items):

        if not items:

            return "No recommendations available."

        lines = [

            "💡 Recommendations",

            ""

        ]

        for item in items:

            lines.append(

                f"• {item}"

            )

        return "\n".join(lines)

    # =====================================================
    # ADVISOR
    # =====================================================

    @staticmethod
    def advisor(items):

        if not items:

            return "No advice available."

        lines = [

            "🧠 Financial Advisor",

            ""

        ]

        for item in items:

            lines.append(

                f"• {item}"

            )

        return "\n".join(lines)

    # =====================================================
    # SIMPLE VALUE
    # =====================================================

    @staticmethod
    def value(title, amount):

        return (

            f"{title}: "

            f"{ResponseBuilder.money(amount)}"

        )

    # =====================================================
    # YES / NO
    # =====================================================

    @staticmethod
    def yes_no(value):

        return "Yes" if value else "No"