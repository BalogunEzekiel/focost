from flask import session

from app.services.dashboard_service import DashboardService
from app.services.llm_service import LLMService


class AIService:

    llm = LLMService()

    @staticmethod
    def build_system_prompt(user_id):

        dashboard = DashboardService.get_dashboard_data(user_id)

        print(dashboard.get("yesterday_summary"))

        budgets = dashboard.get("budget_overview", [])
        goals = dashboard.get("goal_progress", [])

        prompt = f"""
You are FOCOST AI, a personal financial coach.

Use ONLY the financial data provided below.
Never invent balances, transactions, budgets, goals or forecasts.
If information is unavailable, say so.

Projected figures are AI forecasts based on historical financial patterns and machine learning model.
Always answer briefly using simple English.
Use headings or bullet points only when helpful.
Give practical financial advice.

==============================
### SUMMARY
==============================

Available Balance:
₦{dashboard.get("balance", 0):,.2f}

Income This Month:
₦{dashboard.get("income", 0):,.2f}

Expenses This Month:
₦{dashboard.get("expenses", 0):,.2f}

Savings:
₦{dashboard.get("savings", 0):,.2f}

Rate:
{dashboard.get("savings_rate", 0):.2f}%

Health:
{dashboard.get("health_score", 0)}/100

==============================
### BUDGETS
==============================
"""

        if budgets:

            for budget in budgets[:3]:
                prompt += (
                    f"{budget.category}: "
                    f"₦{float(budget.spent):,.0f}/"
                    f"₦{float(budget.amount):,.0f} "
                    f"({budget.status})\n"
                )

        else:

            prompt += "\nNo active budgets.\n"

        prompt += """

==============================
### GOALS
==============================
"""

        if goals:

            for goal in goals[:3]:
                prompt += (
                    f"{goal.get('title')}: "
                    f"{goal.get('percentage',0):.0f}% "
                    f"(₦{goal.get('saved',0):,.0f}/"
                    f"₦{goal.get('target',0):,.0f})\n"
                )

        else:

            prompt += "\nNo active financial goals.\n"

        prompt += """
==============================
### TOP SPENDING
==============================
"""
        top_spending = dashboard.get("top_spending")
        top_spending_amount = dashboard.get("top_spending_amount", 0)

        if top_spending:

            prompt += f"""
        Category: {top_spending}
        Amount: ₦{top_spending_amount:,.2f}
        """
    
        else:

            prompt += "\nNo spending analysis available.\n"

        prompt += """

==============================
### TOP INCOME
==============================
"""

        top_income = dashboard.get("top_income_source")
        top_income_amount = dashboard.get("top_income_amount", 0)

        if top_income:

            prompt += f"""
        Source: {top_income}
        Amount: ₦{top_income_amount:,.2f}
        """

        else:

            prompt += "\nNo income source analysis available.\n"

        prompt += """

==============================
### TRANSACTIONS
==============================
"""

        transactions = dashboard.get("recent_transactions", [])

        if transactions:

            for txn in transactions[:2]:
                prompt += (
                    f"{txn.get('date')} | "
                    f"{txn.get('category')} | "
                    f"₦{txn.get('amount',0):,.0f}\n"
                )

        else:

            prompt += "\nNo recent transactions.\n"

        yesterday = dashboard.get("yesterday_summary", {})

        prompt += f"""

==============================
### YESTERDAY
==============================

Income:
₦{yesterday.get("income", 0):,.2f}

Expenses:
₦{yesterday.get("expenses", 0):,.2f}

Balance:
₦{yesterday.get("balance", 0):,.2f}

Transactions:
{yesterday.get("transactions", 0)}


==============================
### TREND
==============================

Trend:
{dashboard.get("spending_trend", "Unavailable")}

==============================
### CASH FLOW
==============================

Status:
{dashboard.get("cashflow_status", "Unavailable")}

==============================
BUDGET STATUS
==============================

Status:
{dashboard.get("budget_status", "Unavailable")}

==============================
### FORECAST
==============================

Projected Income:
₦{dashboard.get("forecast_income", 0):,.2f}

Projected Expenses:
₦{dashboard.get("forecast_expenses", 0):,.2f}

Projected Savings:
₦{dashboard.get("forecast_balance", 0):,.2f}

Forecast Status:
{dashboard.get("forecast_status", "Unavailable")}

==============================
### RECOMMENDATIONS
==============================
"""

        recommendations = dashboard.get("recommendations", [])

        if recommendations:

            if isinstance(recommendations, list):

                
                for item in recommendations[:2]:

                    prompt += f"• {item}\n"

            else:

                prompt += f"{recommendations}\n"

        else:

            prompt += "\nNo recommendations available.\n"

        prompt += """

==============================
### DAILY BRIEF
==============================
"""

        daily_brief = dashboard.get("daily_brief")

        if daily_brief:

            if isinstance(daily_brief, dict):

                for key, value in list(daily_brief.items())[:2]:

                    prompt += f"{key}: {value}\n"

            else:

                prompt += f"{daily_brief}\n"

        else:

            prompt += "\nNo daily brief available.\n"

        prompt += """

        
     
==============================
YOUR ROLE
==============================

Respond briefly in simple Nigerian English.
Use only the financial data above.
Never invent financial information.

"""

        return prompt

    @staticmethod
    def chat(user_id, message):

        system_prompt = AIService.build_system_prompt(user_id)

        history = session.get("ai_history", [])

        result = AIService.llm.chat(
            user_message=message,
            system_prompt=system_prompt,
            history=history
        )

        if result.get("success"):

            history.append({
                "role": "user",
                "content": message
            })

            history.append({
                "role": "assistant",
                "content": result["message"]
            })

            session["ai_history"] = history[0:]

        return result